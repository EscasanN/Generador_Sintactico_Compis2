"""Activation records, closure environments and the extended symbol table.

``build_runtime_layouts`` is the single entry point: from the persistent
``SymbolTable`` and the per-node ``SemanticAnnotations`` it computes

* the label, size, alignment and offset of every symbol,
* one ``ActivationRecordLayout`` per function/method (plus one for global code),
* one ``ClassLayout`` per class (base-class fields first),
* the captured variables of each closure and the lexical distance to them.

It emits no TAC. Temporary slots are reserved afterwards from the IR's
``peak_active`` through ``RuntimeLayouts.with_temporary_peaks``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from enum import Enum
from types import MappingProxyType

from src.codegen.layout import (
    WORD_SIZE,
    ClassLayout,
    LabelRegistry,
    LayoutBuilder,
    LayoutError,
    Region,
    StorageClass,
    SymbolLayout,
    SymbolLayoutTable,
    align_up,
    check_no_overlap,
    layout_of,
)
from src.semantic.results import SemanticAnnotations
from src.semantic.symbol_table import Scope, ScopeKind, Symbol, SymbolKind, SymbolTable
from src.semantic.types import UNKNOWN, ClassType, Type

CALLABLE_KINDS = frozenset({SymbolKind.FUNCTION, SymbolKind.METHOD})
STORAGE_KINDS = frozenset({SymbolKind.VARIABLE, SymbolKind.CONSTANT})
HEADER_FIELDS = ("return_address", "control_link", "access_link", "return_value")
GLOBAL_FRAME_LABEL = "global"


# ---------------------------------------------------------------- scope helpers


def enclosing_function(scope: Scope | None) -> Scope | None:
    """The nearest function scope containing ``scope`` (itself included)."""
    while scope is not None:
        if scope.kind is ScopeKind.FUNCTION:
            return scope
        scope = scope.parent
    return None


def parent_function(scope: Scope) -> Scope | None:
    """The function scope lexically enclosing the function ``scope``."""
    return enclosing_function(scope.parent)


def lexical_level(scope: Scope | None) -> int:
    """Number of function scopes from ``scope`` up (itself included); 0 = program."""
    level = 0
    while scope is not None:
        if scope.kind is ScopeKind.FUNCTION:
            level += 1
        scope = scope.parent
    return level


def function_symbol_of(scope: Scope) -> Symbol | None:
    """The function or method ``Symbol`` whose body is ``scope``."""
    if scope.kind is not ScopeKind.FUNCTION or scope.parent is None:
        return None
    symbol = scope.parent.resolve_local(scope.name)
    return symbol if symbol is not None and symbol.kind in CALLABLE_KINDS else None


def _is_ancestor_or_same(candidate: Scope, scope: Scope | None) -> bool:
    while scope is not None:
        if scope is candidate:
            return True
        scope = parent_function(scope)
    return False


# ------------------------------------------------------------------ frame model


class FrameSlotKind(Enum):
    HEADER = "header"
    PARAMETER = "parameter"
    LOCAL = "local"
    CAPTURED = "captured"
    TEMPORARY = "temporary"


@dataclass(frozen=True, slots=True)
class FrameSlot:
    """One aligned area of an activation record."""

    name: str
    kind: FrameSlotKind
    offset: int
    size: int
    alignment: int
    type: Type | None = None
    symbol: Symbol | None = None
    hidden: bool = False

    def __post_init__(self) -> None:
        if self.size <= 0 or self.alignment <= 0:
            raise LayoutError(f"slot {self.name} needs a positive size and alignment")
        if self.offset < 0 or self.offset % self.alignment:
            raise LayoutError(
                f"slot {self.name} at {self.offset} is not aligned to {self.alignment}"
            )

    @property
    def end(self) -> int:
        return self.offset + self.size

    @property
    def region(self) -> Region:
        return Region(self.name, self.offset, self.size)


@dataclass(frozen=True, slots=True)
class EnvironmentSlot:
    """A captured variable stored in a closure environment."""

    symbol: Symbol
    offset: int
    size: int
    alignment: int


@dataclass(frozen=True, slots=True)
class EnvironmentLayout:
    """The environment a function builds for the closures defined inside it.

    Captured variables occupy offsets from 0; the access link to the creator's
    own environment follows at ``parent_offset``. ``heap`` is the HEAP_ENV
    decision: some closure using this environment may outlive the frame.
    """

    owner: str
    slots: tuple[EnvironmentSlot, ...]
    parent_offset: int
    size: int
    heap: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "slots", tuple(self.slots))
        regions = [Region(s.symbol.name, s.offset, s.size) for s in self.slots]
        regions.append(Region("access_link", self.parent_offset, WORD_SIZE))
        check_no_overlap(regions, f"environment of {self.owner}")
        if self.size % WORD_SIZE or self.size < self.parent_offset + WORD_SIZE:
            raise LayoutError(f"invalid environment size for {self.owner}")

    def offset_of(self, symbol: Symbol) -> int:
        for slot in self.slots:
            if slot.symbol is symbol:
                return slot.offset
        raise LookupError(f"'{symbol.name}' is not captured by {self.owner}")


@dataclass(frozen=True, slots=True)
class CaptureInfo:
    """A non-local variable used by a function.

    ``depth`` counts access-link hops from the environment the function
    receives: 0 reads it directly from that ``env`` (defined by the enclosing
    function), 1 follows one access link, and so on.
    """

    symbol: Symbol
    owner_frame: str
    depth: int
    env_offset: int


@dataclass(frozen=True, slots=True)
class ActivationRecordLayout:
    """Layout of one activation: header, hidden/declared parameters, locals, temps."""

    label: str
    name: str
    level: int
    slots: tuple[FrameSlot, ...]
    size: int
    function: Symbol | None = None
    alignment: int = WORD_SIZE
    captures: tuple[CaptureInfo, ...] = ()
    environment: EnvironmentLayout | None = None
    needs_env: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "slots", tuple(self.slots))
        object.__setattr__(self, "captures", tuple(self.captures))
        self.validate()

    def validate(self) -> None:
        """Header complete and first, aligned slots, no overlap, unique names."""
        header = [slot for slot in self.slots if slot.kind is FrameSlotKind.HEADER]
        if tuple(slot.name for slot in header) != HEADER_FIELDS:
            raise LayoutError(
                f"{self.label}: header must contain {', '.join(HEADER_FIELDS)}"
            )
        names = [slot.name for slot in self.slots]
        if len(set(names)) != len(names):
            raise LayoutError(f"{self.label}: duplicate slot names")
        check_no_overlap((slot.region for slot in self.slots), f"frame {self.label}")
        end = max(slot.end for slot in self.slots)
        if self.size < end or self.size % self.alignment:
            raise LayoutError(f"{self.label}: frame size {self.size} does not cover its slots")

    def slot(self, name: str) -> FrameSlot:
        for slot in self.slots:
            if slot.name == name:
                return slot
        raise LookupError(f"{self.label} has no slot '{name}'")

    @property
    def header(self) -> tuple[FrameSlot, ...]:
        return tuple(s for s in self.slots if s.kind is FrameSlotKind.HEADER)

    @property
    def hidden_parameters(self) -> tuple[FrameSlot, ...]:
        return tuple(s for s in self.slots if s.hidden)

    @property
    def parameters(self) -> tuple[FrameSlot, ...]:
        return tuple(
            s for s in self.slots if s.kind is FrameSlotKind.PARAMETER and not s.hidden
        )

    @property
    def locals(self) -> tuple[FrameSlot, ...]:
        return tuple(
            s for s in self.slots if s.kind in (FrameSlotKind.LOCAL, FrameSlotKind.CAPTURED)
        )

    @property
    def temporaries(self) -> tuple[FrameSlot, ...]:
        return tuple(s for s in self.slots if s.kind is FrameSlotKind.TEMPORARY)

    @property
    def temporary_capacity(self) -> int:
        return len(self.temporaries)

    def require_temporaries(self, peak: int) -> None:
        """Reject a frame with fewer temporary slots than the IR's live peak."""
        if self.temporary_capacity < peak:
            raise LayoutError(
                f"{self.label}: {self.temporary_capacity} temporary slots "
                f"for a peak of {peak}"
            )

    def with_temporaries(self, peak: int) -> "ActivationRecordLayout":
        """A copy reserving exactly ``peak`` word-sized temporary slots."""
        if type(peak) is not int or peak < 0:
            raise LayoutError("temporary peak must be a nonnegative integer")
        kept = tuple(s for s in self.slots if s.kind is not FrameSlotKind.TEMPORARY)
        cursor = max(slot.end for slot in kept)
        slots = list(kept)
        for index in range(peak):
            offset = align_up(cursor, WORD_SIZE)
            slots.append(
                FrameSlot(f"t{index}", FrameSlotKind.TEMPORARY, offset, WORD_SIZE, WORD_SIZE)
            )
            cursor = offset + WORD_SIZE
        return replace(self, slots=tuple(slots), size=align_up(cursor, self.alignment))


class ActivationRecordBuilder:
    """Ordered reservation: header, hidden parameters, parameters, locals, temporaries."""

    _ORDER = ("header", "hidden", "parameter", "local", "temporary")

    def __init__(
        self,
        label: str,
        name: str,
        level: int,
        function: Symbol | None = None,
    ) -> None:
        self.label = label
        self.name = name
        self.level = level
        self.function = function
        self._layout = LayoutBuilder(f"frame {label}")
        self._slots: list[FrameSlot] = []
        self._symbols: list[SymbolLayout] = []
        self._phase = -1
        self._finished = False

    @property
    def symbol_layouts(self) -> tuple[SymbolLayout, ...]:
        return tuple(self._symbols)

    def _enter(self, phase: str) -> None:
        if self._finished:
            raise LayoutError(f"{self.label}: frame already finalized")
        index = self._ORDER.index(phase)
        if index < self._phase:
            raise LayoutError(f"{self.label}: cannot reserve {phase} after {self._ORDER[self._phase]}")
        if index > 0 and self._phase < 0:
            raise LayoutError(f"{self.label}: reserve the header first")
        self._phase = index

    def _unique_name(self, name: str) -> str:
        """Shadowed symbols keep one slot each; later ones get a ``#n`` suffix."""
        taken = {slot.name for slot in self._slots}
        if name not in taken:
            return name
        number = 2
        while f"{name}#{number}" in taken:
            number += 1
        return f"{name}#{number}"

    def _add(
        self,
        name: str,
        kind: FrameSlotKind,
        size: int,
        alignment: int,
        type_: Type | None = None,
        symbol: Symbol | None = None,
        hidden: bool = False,
    ) -> FrameSlot:
        if symbol is not None:
            name = self._unique_name(name)
        offset = self._layout.allocate(name, size, alignment)
        slot = FrameSlot(name, kind, offset, size, alignment, type_, symbol, hidden)
        self._slots.append(slot)
        return slot

    def reserve_header(self) -> None:
        """Return address, control link, access link and the return-value area."""
        self._enter("header")
        if self._slots:
            raise LayoutError(f"{self.label}: header already reserved")
        for name in HEADER_FIELDS:
            self._add(name, FrameSlotKind.HEADER, WORD_SIZE, WORD_SIZE)

    def reserve_hidden(self, name: str, type_: Type | None = None) -> FrameSlot:
        """A hidden parameter such as ``this`` or ``env`` (one word)."""
        self._enter("hidden")
        return self._add(
            name, FrameSlotKind.PARAMETER, WORD_SIZE, WORD_SIZE, type_, hidden=True
        )

    def _reserve_symbol(
        self,
        phase: str,
        slot_kind: FrameSlotKind,
        storage: StorageClass,
        symbol: Symbol,
        scope_name: str,
        level: int,
        captured: bool,
        env_offset: int | None,
    ) -> SymbolLayout:
        self._enter(phase)
        layout = layout_of(symbol.type)
        slot = self._add(
            symbol.name, slot_kind, layout.size, layout.alignment, symbol.type, symbol
        )
        entry = SymbolLayout(
            symbol,
            storage,
            layout.size,
            layout.alignment,
            offset=slot.offset,
            level=level,
            frame=self.label,
            captured=captured,
            env_offset=env_offset,
            scope_name=scope_name,
        )
        self._symbols.append(entry)
        return entry

    def reserve_parameter(
        self,
        symbol: Symbol,
        *,
        captured: bool = False,
        env_offset: int | None = None,
        scope_name: str | None = None,
    ) -> SymbolLayout:
        return self._reserve_symbol(
            "parameter",
            FrameSlotKind.PARAMETER,
            StorageClass.PARAMETER,
            symbol,
            scope_name or self.name,
            self.level,
            captured,
            env_offset,
        )

    def reserve_local(
        self,
        symbol: Symbol,
        *,
        captured: bool = False,
        env_offset: int | None = None,
        scope_name: str | None = None,
    ) -> SymbolLayout:
        return self._reserve_symbol(
            "local",
            FrameSlotKind.CAPTURED if captured else FrameSlotKind.LOCAL,
            StorageClass.CAPTURED if captured else StorageClass.LOCAL,
            symbol,
            scope_name or self.name,
            self.level,
            captured,
            env_offset,
        )

    def reserve_temporaries(self, peak: int) -> None:
        """Reserve ``peak`` word-sized slots for the maximum live temporaries."""
        self._enter("temporary")
        if peak < 0:
            raise LayoutError("temporary peak cannot be negative")
        for index in range(peak):
            self._add(f"t{index}", FrameSlotKind.TEMPORARY, WORD_SIZE, WORD_SIZE)

    def build(
        self,
        captures: Iterable[CaptureInfo] = (),
        environment: EnvironmentLayout | None = None,
        needs_env: bool = False,
    ) -> ActivationRecordLayout:
        if self._phase < 0:
            raise LayoutError(f"{self.label}: the header was never reserved")
        self._finished = True
        self._layout.validate()
        return ActivationRecordLayout(
            self.label,
            self.name,
            self.level,
            tuple(self._slots),
            self._layout.total_size(),
            self.function,
            captures=tuple(captures),
            environment=environment,
            needs_env=needs_env,
        )


# --------------------------------------------------------------------- captures


@dataclass(frozen=True, slots=True)
class _Use:
    symbol: Symbol
    user: Scope
    owner: Scope


class CaptureAnalysis:
    """Which variables are captured, by whom, and how far away they live.

    A reference is a capture when it appears inside a function, its ``Symbol``
    was declared in an enclosing *function*, and it is neither global nor a
    member reached through ``this``. Functions, methods and classes are linked
    by label, so a recursive function never captures itself.
    """

    def __init__(
        self,
        annotations: SemanticAnnotations,
        symbol_table: SymbolTable,
        root: object | None = None,
    ) -> None:
        self.owner_scope: dict[int, Scope] = {}
        for scope in symbol_table.iter_scopes():
            for symbol in scope.symbols:
                self.owner_scope[id(symbol)] = scope
        self._escaping = _escaping_functions(annotations, root)
        self._uses: list[_Use] = []
        seen: set[tuple[int, int]] = set()
        for node_id, scope in annotations.scopes_by_node.items():
            symbol = annotations.symbols_by_node.get(node_id)
            if symbol is None or symbol.kind not in (
                SymbolKind.VARIABLE,
                SymbolKind.CONSTANT,
                SymbolKind.PARAMETER,
            ):
                continue
            declared = self.owner_scope.get(id(symbol))
            user = enclosing_function(scope)
            owner = enclosing_function(declared)
            if declared is None or owner is None or user is None or owner is user:
                continue
            if not _is_ancestor_or_same(owner, user):
                continue
            key = (id(symbol), id(user))
            if key not in seen:
                seen.add(key)
                self._uses.append(_Use(symbol, user, owner))

        self.captured: dict[int, Symbol] = {}
        self.needs_env: set[int] = set()
        self.heap_owners: set[int] = set()
        self.captured_by_owner: dict[int, list[Symbol]] = {}
        self.uses_by_function: dict[int, list[_Use]] = {}
        for use in self._uses:
            self.uses_by_function.setdefault(id(use.user), []).append(use)
            if id(use.symbol) not in self.captured:
                self.captured[id(use.symbol)] = use.symbol
                self.captured_by_owner.setdefault(id(use.owner), []).append(use.symbol)
            function: Scope | None = use.user
            while function is not None and function is not use.owner:
                self.needs_env.add(id(function))
                if self._escapes(function):
                    creator = parent_function(function)
                    while creator is not None:
                        self.heap_owners.add(id(creator))
                        if creator is use.owner:
                            break
                        creator = parent_function(creator)
                function = parent_function(function)

        self.env_offsets: dict[int, int] = {}
        for symbols in self.captured_by_owner.values():
            cursor = 0
            for symbol in symbols:
                layout = layout_of(symbol.type)
                cursor = align_up(cursor, layout.alignment)
                self.env_offsets[id(symbol)] = cursor
                cursor += layout.size

    def _escapes(self, function: Scope) -> bool:
        if self._escaping is None:
            return True
        symbol = function_symbol_of(function)
        return symbol is not None and id(symbol) in self._escaping

    def is_captured(self, symbol: Symbol) -> bool:
        return id(symbol) in self.captured

    def creates_environment(self, function: Scope, nested: Iterable[Scope]) -> bool:
        """True when ``function`` owns captured variables or forwards the chain."""
        if id(function) in self.captured_by_owner:
            return True
        return any(
            id(inner) in self.needs_env and parent_function(inner) is function
            for inner in nested
        )


def _escaping_functions(
    annotations: SemanticAnnotations,
    root: object | None,
) -> set[int] | None:
    """Identity set of function symbols used as a value; ``None`` when unknown.

    A function whose only references are direct calls (``f(...)``) cannot
    outlive its creator's frame. Anything else (assigned, returned, passed)
    counts as an escape. Without the syntax tree every function is assumed to
    escape.
    """
    if root is None:
        return None
    parent: dict[int, object] = {}
    stack = [root]
    while stack:
        node = stack.pop()
        for child in getattr(node, "children", ()):
            parent[id(child)] = node
            stack.append(child)
    nodes = {id(anchor): anchor for anchor in annotations.anchors}
    escaping: set[int] = set()
    for node_id, symbol in annotations.symbols_by_node.items():
        node = nodes.get(node_id)
        if (
            symbol.kind is not SymbolKind.FUNCTION
            or node is None
            or getattr(node, "alternative", None) != "IdentifierExpr"
        ):
            continue
        atom = parent.get(id(node))
        call = parent.get(id(atom)) if atom is not None else None
        is_callee = (
            atom is not None
            and getattr(atom, "alternative", None) == "LeftHandSideAtom"
            and call is not None
            and getattr(call, "alternative", None) in {"CallExprNoArgs", "CallExprWithArgs"}
            and call.children
            and call.children[0] is atom
        )
        if not is_callee:
            escaping.add(id(symbol))
    return escaping


# ---------------------------------------------------------------- runtime layouts


@dataclass(frozen=True, slots=True)
class RuntimeLayouts:
    """Everything the generator needs about memory, labels and activations."""

    symbols: SymbolLayoutTable
    classes: Mapping[str, ClassLayout]
    frames: tuple[ActivationRecordLayout, ...]
    global_frame: ActivationRecordLayout
    captures: CaptureAnalysis = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "classes", MappingProxyType(dict(self.classes)))
        object.__setattr__(self, "frames", tuple(self.frames))

    def frame_by_label(self, label: str) -> ActivationRecordLayout:
        if label == self.global_frame.label:
            return self.global_frame
        for frame in self.frames:
            if frame.label == label:
                return frame
        raise LookupError(f"no activation record labelled '{label}'")

    def frame_for(self, function: Symbol) -> ActivationRecordLayout:
        """The activation record of a function or method symbol (by identity)."""
        for frame in self.frames:
            if frame.function is function:
                return frame
        raise LookupError(f"no activation record for '{function.name}'")

    def class_layout(self, owner: Symbol | ClassType | str) -> ClassLayout:
        """Class layout by symbol, class type or class name."""
        name = owner if isinstance(owner, str) else owner.name
        try:
            return self.classes[name]
        except KeyError:
            raise LookupError(f"no layout for class '{name}'") from None

    def with_temporary_peaks(
        self,
        peaks: Mapping[str, int],
        global_peak: int | None = None,
    ) -> "RuntimeLayouts":
        """Reserve each frame's temporary slots from the IR's ``peak_active``."""
        unknown = set(peaks) - {frame.label for frame in self.frames}
        if unknown:
            raise LookupError(f"unknown activation labels: {sorted(unknown)}")
        frames = tuple(
            frame.with_temporaries(peaks[frame.label]) if frame.label in peaks else frame
            for frame in self.frames
        )
        global_frame = (
            self.global_frame
            if global_peak is None
            else self.global_frame.with_temporaries(global_peak)
        )
        return replace(self, frames=frames, global_frame=global_frame)

    def finalize_temporaries(self, program: object, global_peak: int = 0) -> "RuntimeLayouts":
        """Like ``with_temporary_peaks`` using an ``IRProgram``'s procedures."""
        peaks = {
            str(procedure.label.value): procedure.temporary_peak
            for procedure in program.procedures  # type: ignore[attr-defined]
        }
        return self.with_temporary_peaks(peaks, global_peak)


def _base_label(scope: Scope, symbol: Symbol) -> str:
    parts = [
        ancestor.name
        for ancestor in _ancestors(scope)
        if ancestor.kind in (ScopeKind.FUNCTION, ScopeKind.CLASS)
    ]
    path = ".".join([*parts, symbol.name])
    return f"fn_{path}" if symbol.kind is SymbolKind.FUNCTION else path


def _ancestors(scope: Scope) -> list[Scope]:
    chain: list[Scope] = []
    current: Scope | None = scope
    while current is not None:
        chain.append(current)
        current = current.parent
    chain.reverse()
    return chain


def build_runtime_layouts(
    symbol_table: SymbolTable,
    annotations: SemanticAnnotations,
    root: object | None = None,
) -> RuntimeLayouts:
    """Compute labels, class layouts, activation records and the extended table."""
    scopes = tuple(symbol_table.iter_scopes())
    analysis = CaptureAnalysis(annotations, symbol_table, root)
    registry = LabelRegistry()

    labels: dict[int, str] = {}
    for scope in scopes:
        for symbol in scope.symbols:
            if symbol.kind in CALLABLE_KINDS or symbol.kind is SymbolKind.CLASS:
                labels[id(symbol)] = registry.unique(_base_label(scope, symbol))

    entries: list[SymbolLayout] = []

    # Code symbols: labelled, one word, no storage offset.
    for scope in scopes:
        for symbol in scope.symbols:
            if id(symbol) in labels:
                entries.append(
                    SymbolLayout(
                        symbol,
                        StorageClass.STATIC,
                        WORD_SIZE,
                        WORD_SIZE,
                        label=labels[id(symbol)],
                        level=lexical_level(scope),
                        scope_name=scope.name,
                    )
                )

    classes = _build_classes(scopes, labels, entries)

    # Static variables: program scope and blocks outside any function.
    static = LayoutBuilder("the static area")
    for scope in scopes:
        if scope.kind not in (ScopeKind.GLOBAL, ScopeKind.BLOCK):
            continue
        if enclosing_function(scope) is not None:
            continue
        for symbol in scope.symbols:
            if symbol.kind in STORAGE_KINDS:
                offset, layout = static.allocate_type(symbol.name, symbol.type)
                entries.append(
                    SymbolLayout(
                        symbol,
                        StorageClass.STATIC,
                        layout.size,
                        layout.alignment,
                        offset=offset,
                        level=0,
                        scope_name=scope.name,
                    )
                )
    static.validate()

    frames: list[ActivationRecordLayout] = []
    for scope in scopes:
        if scope.kind is not ScopeKind.FUNCTION:
            continue
        function = function_symbol_of(scope)
        if function is None:
            continue
        frame, symbol_layouts = _build_frame(scope, function, labels, analysis, scopes)
        frames.append(frame)
        entries.extend(symbol_layouts)

    global_builder = ActivationRecordBuilder(GLOBAL_FRAME_LABEL, "program", 0)
    global_builder.reserve_header()
    global_frame = global_builder.build()

    table = SymbolLayoutTable(entries, static_size=static.total_size())
    return RuntimeLayouts(table, classes, tuple(frames), global_frame, analysis)


def _build_classes(
    scopes: tuple[Scope, ...],
    labels: dict[int, str],
    entries: list[SymbolLayout],
) -> dict[str, ClassLayout]:
    declared: dict[str, tuple[Scope, Symbol]] = {}
    for scope in scopes:
        for symbol in scope.symbols:
            if symbol.kind is SymbolKind.CLASS and isinstance(symbol.type, ClassType):
                declared[symbol.name] = (scope, symbol)
    built: dict[str, ClassLayout] = {}

    def build(name: str, active: tuple[str, ...]) -> ClassLayout:
        if name in built:
            return built[name]
        if name in active:
            raise LayoutError(f"inheritance cycle through class '{name}'")
        scope, symbol = declared[name]
        assert isinstance(symbol.type, ClassType)
        base_type = symbol.type.superclass
        base = build(base_type.name, (*active, name)) if base_type and base_type.name in declared else None
        label = labels[id(symbol)]
        builder = LayoutBuilder(f"class {label}", start=base.size if base else 0)
        members = symbol.metadata.get("members", {})
        own: list[SymbolLayout] = []
        methods: dict[str, str] = {}
        for member_name, member in members.items():
            if member.kind is SymbolKind.FIELD:
                offset, layout = builder.allocate_type(member_name, member.type)
                own.append(
                    SymbolLayout(
                        member,
                        StorageClass.FIELD,
                        layout.size,
                        layout.alignment,
                        offset=offset,
                        level=lexical_level(scope),
                        frame=label,
                        scope_name=symbol.name,
                    )
                )
            elif member.kind is SymbolKind.METHOD and id(member) in labels:
                methods[member_name] = labels[id(member)]
        builder.validate()
        entries.extend(own)
        layout = ClassLayout(
            symbol,
            label,
            max(builder.total_size(), WORD_SIZE),
            WORD_SIZE,
            tuple(own),
            base.all_fields if base else (),
            methods,
            f"{label}.constructor",
            "constructor" in methods,
            base,
        )
        built[name] = layout
        return layout

    for name in declared:
        build(name, ())
    return built


def _build_frame(
    scope: Scope,
    function: Symbol,
    labels: dict[int, str],
    analysis: CaptureAnalysis,
    scopes: tuple[Scope, ...],
) -> tuple[ActivationRecordLayout, tuple[SymbolLayout, ...]]:
    label = labels[id(function)]
    level = lexical_level(scope)
    nested = tuple(
        inner
        for inner in scopes
        if inner.kind is ScopeKind.FUNCTION and parent_function(inner) is scope
    )

    # Environment: captured variables owned by this function.
    captured_symbols = analysis.captured_by_owner.get(id(scope), [])
    environment: EnvironmentLayout | None = None
    if analysis.creates_environment(scope, nested):
        env_builder = LayoutBuilder(f"environment of {label}")
        env_slots = []
        for symbol in captured_symbols:
            offset, layout = env_builder.allocate_type(symbol.name, symbol.type)
            assert offset == analysis.env_offsets[id(symbol)]
            env_slots.append(EnvironmentSlot(symbol, offset, layout.size, layout.alignment))
        parent_offset = env_builder.allocate("access_link", WORD_SIZE, WORD_SIZE)
        environment = EnvironmentLayout(
            label,
            tuple(env_slots),
            parent_offset,
            env_builder.total_size(),
            heap=id(scope) in analysis.heap_owners,
        )

    builder = ActivationRecordBuilder(label, function.name, level, function)
    builder.reserve_header()
    parent_scope = scope.parent
    if function.kind is SymbolKind.METHOD and parent_scope is not None:
        class_symbol = (
            parent_scope.parent.resolve_local(parent_scope.name)
            if parent_scope.kind is ScopeKind.CLASS and parent_scope.parent
            else None
        )
        builder.reserve_hidden("this", class_symbol.type if class_symbol else UNKNOWN)
    needs_env = id(scope) in analysis.needs_env
    if needs_env:
        builder.reserve_hidden("env")

    def env_of(symbol: Symbol) -> tuple[bool, int | None]:
        return (id(symbol) in analysis.env_offsets, analysis.env_offsets.get(id(symbol)))

    for symbol in scope.symbols:
        if symbol.kind is SymbolKind.PARAMETER:
            captured, env_offset = env_of(symbol)
            builder.reserve_parameter(symbol, captured=captured, env_offset=env_offset)

    def reserve_locals(current: Scope) -> None:
        for symbol in current.symbols:
            if symbol.kind in STORAGE_KINDS:
                captured, env_offset = env_of(symbol)
                builder.reserve_local(
                    symbol,
                    captured=captured,
                    env_offset=env_offset,
                    scope_name=current.name,
                )
        for child in current.children:
            if child.kind is ScopeKind.BLOCK:
                reserve_locals(child)

    reserve_locals(scope)

    captures = tuple(
        CaptureInfo(
            use.symbol,
            labels[id(owner_function)] if (owner_function := function_symbol_of(use.owner)) else GLOBAL_FRAME_LABEL,
            lexical_level(use.user) - lexical_level(use.owner) - 1,
            analysis.env_offsets[id(use.symbol)],
        )
        for use in analysis.uses_by_function.get(id(scope), [])
    )
    frame = builder.build(captures, environment, needs_env)
    return frame, builder.symbol_layouts


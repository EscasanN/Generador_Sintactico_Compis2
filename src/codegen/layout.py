"""Storage classes, sizes, offsets and labels for the extended symbol table.

The memory model is the abstract 64-bit machine described in ``DISENO_TAC.md``.
Offsets are bytes, always aligned, and never overlap inside one region (the
static area, one activation record, one class instance or one environment).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType

from src.codegen.contracts import Address
from src.semantic.symbol_table import Symbol
from src.semantic.types import BOOLEAN, INTEGER, Type


class LayoutError(ValueError):
    """A size, alignment, offset or label rule of the memory model was violated."""


class DuplicateLabelError(LayoutError):
    """A label was claimed twice in one compilation unit."""


class StorageClass(Enum):
    """Where a symbol lives at run time."""

    STATIC = "static"
    PARAMETER = "parameter"
    LOCAL = "local"
    FIELD = "field"
    CAPTURED = "captured"
    TEMPORARY = "temporary"


@dataclass(frozen=True, slots=True)
class TypeLayout:
    """Size and alignment, both in bytes, of a value of some type."""

    size: int
    alignment: int

    def __post_init__(self) -> None:
        if type(self.size) is not int or self.size <= 0:
            raise LayoutError(f"size must be a positive integer, got {self.size!r}")
        if (
            type(self.alignment) is not int
            or self.alignment <= 0
            or self.alignment & (self.alignment - 1)
        ):
            raise LayoutError(f"alignment must be a power of two, got {self.alignment!r}")


_BOOLEAN = TypeLayout(1, 1)
_INTEGER = TypeLayout(4, 4)
_WORD = TypeLayout(8, 8)

WORD_SIZE = 8


def layout_of(type_: Type) -> TypeLayout:
    """Return the abstract size/alignment of ``type_``.

    boolean 1/1, integer 4/4; float, string, lists, objects, functions and any
    unknown reference are one 8-byte word aligned to 8.
    """
    if type_ == BOOLEAN:
        return _BOOLEAN
    if type_ == INTEGER:
        return _INTEGER
    return _WORD


def align_up(value: int, alignment: int) -> int:
    """Round ``value`` up to a multiple of ``alignment``: ceil(v / a) * a."""
    if alignment <= 0:
        raise LayoutError("alignment must be positive")
    return -(-value // alignment) * alignment


@dataclass(frozen=True, slots=True)
class Region:
    """A named byte interval used to detect overlap."""

    name: str
    offset: int
    size: int

    @property
    def end(self) -> int:
        return self.offset + self.size


def find_overlap(regions: Iterable[Region]) -> tuple[Region, Region] | None:
    """Return the first pair of intersecting regions, or ``None``."""
    ordered = sorted(regions, key=lambda region: (region.offset, region.end))
    for previous, current in zip(ordered, ordered[1:]):
        if current.offset < previous.end:
            return previous, current
    return None


def check_no_overlap(regions: Iterable[Region], area: str) -> None:
    """Raise ``LayoutError`` when two regions of ``area`` intersect."""
    clash = find_overlap(regions)
    if clash is not None:
        first, second = clash
        raise LayoutError(
            f"overlap in {area}: {first.name} [{first.offset}, {first.end}) "
            f"and {second.name} [{second.offset}, {second.end})"
        )


class LayoutBuilder:
    """Sequential, aligned allocation inside one region."""

    def __init__(self, area: str, start: int = 0) -> None:
        if start < 0:
            raise LayoutError("start offset cannot be negative")
        self.area = area
        self._cursor = start
        self._regions: list[Region] = []

    @property
    def cursor(self) -> int:
        """Offset where the next allocation would start before alignment."""
        return self._cursor

    @property
    def regions(self) -> tuple[Region, ...]:
        return tuple(self._regions)

    def allocate(self, name: str, size: int, alignment: int) -> int:
        """Reserve ``size`` bytes aligned to ``alignment`` and return the offset."""
        layout = TypeLayout(size, alignment)
        offset = align_up(self._cursor, layout.alignment)
        self._regions.append(Region(name, offset, layout.size))
        self._cursor = offset + layout.size
        return offset

    def allocate_type(self, name: str, type_: Type) -> tuple[int, TypeLayout]:
        layout = layout_of(type_)
        return self.allocate(name, layout.size, layout.alignment), layout

    def total_size(self, alignment: int = WORD_SIZE) -> int:
        """Size of the region rounded up to ``alignment``."""
        return align_up(self._cursor, alignment)

    def validate(self) -> None:
        check_no_overlap(self._regions, self.area)


class LabelRegistry:
    """Deterministic, unique labels for callables and classes."""

    def __init__(self) -> None:
        self._used: set[str] = set()

    def claim(self, label: str) -> str:
        """Register ``label`` exactly; a repeat raises ``DuplicateLabelError``."""
        if not label:
            raise LayoutError("label cannot be empty")
        if label in self._used:
            raise DuplicateLabelError(f"duplicate label: {label}")
        self._used.add(label)
        return label

    def unique(self, base: str) -> str:
        """Claim ``base`` or, if taken, ``base`` plus the first free ``_n`` suffix."""
        if base not in self._used:
            return self.claim(base)
        number = 2
        while f"{base}_{number}" in self._used:
            number += 1
        return self.claim(f"{base}_{number}")

    def __contains__(self, label: object) -> bool:
        return label in self._used

    def __len__(self) -> int:
        return len(self._used)


@dataclass(frozen=True, slots=True)
class SymbolLayout:
    """The code-generation facts attached to one semantic ``Symbol``.

    ``offset`` is relative to the symbol's region: the static area, its
    activation record, its class instance. Callables and classes have a
    ``label`` instead of an offset. ``level`` is the lexical level of the
    declaring scope (0 = program, +1 per enclosing function). ``frame`` names the
    owning activation record (its label) for parameters, locals and captures.
    For a captured symbol ``env_offset`` is its slot in the owner's environment.
    """

    symbol: Symbol
    storage: StorageClass
    size: int
    alignment: int
    offset: int | None = None
    label: str | None = None
    level: int = 0
    frame: str | None = None
    captured: bool = False
    env_offset: int | None = None
    scope_name: str = "global"

    def __post_init__(self) -> None:
        if not isinstance(self.storage, StorageClass):
            raise LayoutError(f"unknown storage class: {self.storage!r}")
        TypeLayout(self.size, self.alignment)
        if self.offset is not None:
            if self.offset < 0:
                raise LayoutError(f"negative offset for {self.symbol.name}")
            if self.offset % self.alignment:
                raise LayoutError(
                    f"offset {self.offset} of {self.symbol.name} is not aligned "
                    f"to {self.alignment}"
                )
        if self.offset is None and self.label is None:
            raise LayoutError(f"{self.symbol.name} has neither an offset nor a label")
        if self.captured and self.env_offset is None:
            raise LayoutError(f"captured {self.symbol.name} needs an environment offset")

    @property
    def name(self) -> str:
        return self.symbol.name

    @property
    def region(self) -> Region:
        if self.offset is None:
            raise LayoutError(f"{self.symbol.name} occupies no storage region")
        return Region(self.symbol.name, self.offset, self.size)

    def address(self) -> Address:
        """The stable abstract address consumed by ``Operand(SYMBOL, ...)``."""
        scope = None if self.storage is StorageClass.STATIC else self.frame
        return Address(self.symbol, self.storage.value, self.symbol.name, self.offset, scope)


@dataclass(frozen=True, slots=True)
class ClassLayout:
    """Instance layout and method labels of one class."""

    symbol: Symbol
    label: str
    size: int
    alignment: int
    fields: tuple[SymbolLayout, ...]
    inherited: tuple[SymbolLayout, ...] = ()
    methods: Mapping[str, str] = field(default_factory=dict)
    constructor_label: str = ""
    explicit_constructor: bool = False
    superclass: "ClassLayout | None" = None
    environment_offset: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", tuple(self.fields))
        object.__setattr__(self, "inherited", tuple(self.inherited))
        object.__setattr__(self, "methods", MappingProxyType(dict(self.methods)))
        if self.size <= 0 or self.size % self.alignment:
            raise LayoutError(f"invalid instance size for class {self.label}")
        check_no_overlap(
            [*(layout.region for layout in self.all_fields),
             *(Region(f"{owner.label}.$env", offset, WORD_SIZE)
               for owner, offset in self.environment_bindings)], f"class {self.label}"
        )

    @property
    def environment_bindings(self) -> tuple[tuple["ClassLayout", int], ...]:
        inherited = self.superclass.environment_bindings if self.superclass else ()
        own = ((self, self.environment_offset),) if self.environment_offset is not None else ()
        return (*inherited, *own)

    @property
    def all_fields(self) -> tuple[SymbolLayout, ...]:
        """Inherited fields first (base class offsets), then the class's own."""
        return self.inherited + self.fields

    def field_offset(self, name: str) -> int:
        """Offset of ``name``, searching own fields before inherited ones."""
        for layout in reversed(self.all_fields):
            if layout.symbol.name == name:
                assert layout.offset is not None
                return layout.offset
        raise LookupError(f"class {self.label} has no field '{name}'")

    def method_label(self, name: str) -> str:
        """Static label of a method found here or in a base class."""
        layout: ClassLayout | None = self
        while layout is not None:
            if name in layout.methods:
                return layout.methods[name]
            layout = layout.superclass
        raise LookupError(f"class {self.label} has no method '{name}'")


class SymbolLayoutTable:
    """The semantic symbols combined with their code-generation layouts."""

    def __init__(
        self,
        layouts: Iterable[SymbolLayout],
        static_size: int = 0,
    ) -> None:
        self._layouts: list[SymbolLayout] = []
        self._by_symbol: dict[int, SymbolLayout] = {}
        for layout in layouts:
            if id(layout.symbol) in self._by_symbol:
                raise LayoutError(f"symbol laid out twice: {layout.symbol.name}")
            self._by_symbol[id(layout.symbol)] = layout
            self._layouts.append(layout)
        self.static_size = static_size
        self.validate()

    def layout_for(self, symbol: Symbol) -> SymbolLayout:
        """Layout of ``symbol`` by identity; ``LookupError`` when absent."""
        try:
            return self._by_symbol[id(symbol)]
        except KeyError:
            raise LookupError(f"no layout for symbol '{symbol.name}'") from None

    def address_for(self, symbol: Symbol) -> Address:
        return self.layout_for(symbol).address()

    def __contains__(self, symbol: object) -> bool:
        return id(symbol) in self._by_symbol

    def __iter__(self) -> Iterator[SymbolLayout]:
        return iter(tuple(self._layouts))

    def __len__(self) -> int:
        return len(self._layouts)

    def by_storage(self, storage: StorageClass) -> tuple[SymbolLayout, ...]:
        return tuple(layout for layout in self._layouts if layout.storage is storage)

    def labels(self) -> tuple[str, ...]:
        return tuple(layout.label for layout in self._layouts if layout.label is not None)

    def validate(self) -> None:
        """Reject duplicate labels and overlapping slots inside any one region."""
        seen: set[str] = set()
        regions: dict[tuple[str, str | None], list[Region]] = {}
        for layout in self._layouts:
            if layout.label is not None:
                if layout.label in seen:
                    raise DuplicateLabelError(f"duplicate label: {layout.label}")
                seen.add(layout.label)
            if layout.offset is None or layout.storage is StorageClass.FIELD:
                continue
            key = (
                ("static", None)
                if layout.storage is StorageClass.STATIC
                else ("frame", layout.frame)
            )
            regions.setdefault(key, []).append(layout.region)
        for (kind, frame), items in regions.items():
            area = "the static area" if kind == "static" else f"frame {frame}"
            check_no_overlap(items, area)

    def rows(self) -> tuple[dict[str, object], ...]:
        """Plain rows for presentation: name, storage, offset, size, label, level."""
        return tuple(
            {
                "name": layout.symbol.name,
                "kind": layout.symbol.kind.value,
                "type": str(layout.symbol.type),
                "storage": layout.storage.value,
                "offset": layout.offset,
                "size": layout.size,
                "alignment": layout.alignment,
                "label": layout.label,
                "level": layout.level,
                "frame": layout.frame,
                "captured": layout.captured,
                "env_offset": layout.env_offset,
            }
            for layout in self._layouts
        )

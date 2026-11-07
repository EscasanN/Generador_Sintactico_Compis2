"""Physical MIPS32 frames, static data and lexical links (block 2).

The abstract layouts of Project 2 describe a 64-bit machine; this module maps
them to the physical machine of ``DISENO_MIPS.md`` without modifying them:

* every procedure receives a frame whose header occupies the first 32 bytes
  (``ra``, previous ``fp``, access link, return-value backup);
* locals, reusable temporary slots and the outgoing-argument staging area
  follow, all aligned to their access width;
* arguments are *incoming* slots of eight bytes at ``fp + frame_size + 8*i``,
  hidden parameters first, as the caller built them;
* static symbols live in a ``$gp`` based region; object and environment
  offsets are preserved (references use four bytes and keep their padding).

``PhysicalLayoutPlan`` implements the ``LocationResolver`` contract of block 1
and also exposes the signatures that calls and closures need.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from src.codegen.activation import (
    ActivationRecordLayout, EnvironmentLayout, FrameSlotKind, function_symbol_of,
    parent_function,
)
from src.codegen.contracts import Address
from src.codegen.ir import IRProcedure, IRProgram, Instruction, OpCode, Operand, OperandKind
from src.codegen.layout import ClassLayout, StorageClass, align_up
from src.mips.diagnostics import MipsError
from src.mips.models import MachineLocation, validate_locations
from src.semantic.symbol_table import ScopeKind, Symbol
from src.semantic.types import BOOLEAN, FLOAT, ClassType, Type

GLOBAL_UNIT = 'global'
SLOT_SIZE = 8
HEADER_SIZE = 32
RETURN_ADDRESS_OFFSET = 0
CONTROL_LINK_OFFSET = 8
ACCESS_LINK_OFFSET = 16
RETURN_VALUE_OFFSET = 24
HIDDEN_ORDER = ((), ('env',), ('this',), ('this', 'env'))
# `addiu`/`lw`/`sw` immediates are 16-bit signed: a frame and its arguments must stay below.
MAX_FRAME_SIZE = 0x6000


def representation(type_: Type | None) -> str:
    """Register class of a value: doubles travel apart from every other word."""
    return 'double' if type_ == FLOAT else 'word'


def memory_width(type_: Type | None) -> int:
    """Access width of a symbol, field or temporary cell."""
    return 8 if type_ == FLOAT else 1 if type_ == BOOLEAN else 4


def abi_width(type_: Type | None) -> int:
    """Argument slots carry booleans as a normalized word."""
    return 8 if type_ == FLOAT else 4


@dataclass(frozen=True, slots=True)
class ProcedureSignature:
    """Physical signature of a procedure, hidden parameters included."""

    label: str
    parameter_types: tuple[Type, ...]
    hidden: tuple[str, ...]
    returns: str
    return_type: Type | None = None
    bound_environment_offset: int | None = None

    @property
    def arity(self) -> int:
        return len(self.parameter_types)

    @property
    def declared_arity(self) -> int:
        return self.arity - len(self.hidden)

    @property
    def mask(self) -> int:
        """Runtime descriptor mask: bit 0 receives ``env``, bit 1 ``this``."""
        return (1 if 'env' in self.hidden else 0) | (2 if 'this' in self.hidden else 0)


def signature_of(procedure: IRProcedure) -> ProcedureSignature:
    label = str(procedure.label.value)
    types: list[Type] = []
    hidden: list[str] = []
    for index, parameter in enumerate(procedure.parameters):
        if parameter.kind is not OperandKind.SYMBOL or not isinstance(parameter.value, Address):
            raise MipsError('MIPS-INVALID-IR', f'{label}: parameters must be symbols')
        types.append(parameter.type)
        if parameter.value.symbol.metadata.get('codegen_hidden'):
            if index != len(hidden):
                raise MipsError('MIPS-INVALID-IR', f'{label}: hidden parameters must come first')
            hidden.append(parameter.value.name)
    if tuple(hidden) not in HIDDEN_ORDER:
        raise MipsError('MIPS-INVALID-IR', f'{label}: hidden parameters must be this, env or both')
    value_types = [i.arg1.type for i in procedure.instructions
                   if i.opcode is OpCode.RETURN and i.arg1 is not None]
    kinds = {representation(t) for t in value_types}
    if len(kinds) > 1:
        raise MipsError('MIPS-CALL-SIGNATURE', f'{label}: returns mix doubles and words')
    returns = kinds.pop() if kinds else 'void'
    return ProcedureSignature(label, tuple(types), tuple(hidden), returns,
                              value_types[0] if value_types else None,
                              procedure.bound_environment_offset)


@dataclass(frozen=True, slots=True)
class EnvironmentAccess:
    """A lexical cell: follow ``links`` (parent-pointer offsets), then ``offset``."""

    owner: str
    depth: int
    links: tuple[int, ...]
    offset: int
    target: str


@dataclass(frozen=True, slots=True)
class PhysicalFrame:
    """Checked physical map of one activation."""

    label: str
    size: int
    arity: int
    parameters: Mapping[int, MachineLocation]
    locals: Mapping[int, MachineLocation]
    temporaries: Mapping[tuple[int, int], MachineLocation]
    staging: int = 0
    staging_start: int = HEADER_SIZE
    has_env: bool = False

    def __post_init__(self) -> None:
        for name in ('parameters', 'locals', 'temporaries'):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        self.validate()

    def staging_offset(self, index: int) -> int:
        if not 0 <= index < self.staging:
            raise MipsError('MIPS-CALL-ARITY', f'{self.label}: staging slot {index} is not reserved')
        return self.staging_start + SLOT_SIZE * index

    def incoming_offset(self, index: int) -> int:
        if not 0 <= index < self.arity:
            raise MipsError('MIPS-CALL-ARITY', f'{self.label}: no incoming argument {index}')
        return self.size + SLOT_SIZE * index

    def validate(self) -> None:
        if self.size % SLOT_SIZE or self.size < HEADER_SIZE:
            raise MipsError('MIPS-INVALID-ADDRESS', f'{self.label}: invalid frame size {self.size}')
        if self.size + SLOT_SIZE * self.arity > MAX_FRAME_SIZE:
            raise MipsError('MIPS-INVALID-ADDRESS',
                            f'{self.label}: frame of {self.size} bytes exceeds the 16-bit offset range')
        body = [*self.locals.values(), *self.temporaries.values()]
        for location in body:
            if location.base != '$fp' or location.offset < HEADER_SIZE \
                    or location.offset + location.size > self.size:
                raise MipsError('MIPS-INVALID-ADDRESS', f'{self.label}: slot outside the frame body')
        end = self.staging_start + SLOT_SIZE * self.staging
        if self.staging < 0 or self.staging_start % SLOT_SIZE or end > self.size:
            raise MipsError('MIPS-INVALID-ADDRESS', f'{self.label}: staging outside the frame')
        staged = [MachineLocation('$fp', self.staging_start + SLOT_SIZE * i, SLOT_SIZE, 4)
                  for i in range(self.staging)]
        incoming = list(self.parameters.values())
        for location in incoming:
            low = self.size
            if location.base != '$fp' or location.offset < low \
                    or location.offset + location.size > low + SLOT_SIZE * self.arity:
                raise MipsError('MIPS-INVALID-ADDRESS', f'{self.label}: parameter outside incoming area')
        # Leases whose lifetimes are disjoint may deliberately share one cell: only
        # distinct cells can overlap, and every cell must be exactly one slot.
        cells = {(l.offset, l.size): MachineLocation('$fp', l.offset, l.size, 4)
                 for l in self.temporaries.values()}
        if any(size != SLOT_SIZE for _, size in cells):
            raise MipsError('MIPS-INVALID-ADDRESS', f'{self.label}: temporary cells are one slot each')
        try:
            validate_locations([MachineLocation('$fp', 0, HEADER_SIZE, 8),
                                *self.locals.values(), *cells.values(), *staged])
            validate_locations(incoming)
        except ValueError as error:
            raise MipsError('MIPS-INVALID-ADDRESS', f'{self.label}: {error}') from error


def _temporary_intervals(instructions: Sequence[Instruction]) -> dict[tuple[int, int], list]:
    """lease -> [type, first, last]; unreleased leases live until the unit ends.

    A lease reaching into a loop is extended to the loop's back edge so no slot
    is shared with a value that is still needed in the next iteration.
    """
    spans: dict[tuple[int, int], list] = {}
    released: dict[tuple[int, int], int] = {}
    labels: dict[str, int] = {}
    for index, item in enumerate(instructions):
        if item.opcode is OpCode.LABEL and item.result is not None:
            labels[str(item.result.value)] = index
        for operand in (item.arg1, item.arg2, item.result):
            if operand is None or operand.kind is not OperandKind.TEMPORARY:
                continue
            span = spans.setdefault(operand.lease, [operand.type, index, index])
            if span[0] != operand.type:
                raise MipsError('MIPS-TYPE', f'lease {operand.lease} changes machine type',
                                item.source_location)
            span[2] = index
        if item.opcode is OpCode.RELEASE and item.arg1 is not None \
                and item.arg1.kind is OperandKind.TEMPORARY:
            released.setdefault(item.arg1.lease, index)
    last = len(instructions)
    for lease, span in spans.items():
        span[2] = released.get(lease, last)
    loops = [(labels[str(i.result.value)], index) for index, i in enumerate(instructions)
             if i.opcode in (OpCode.GOTO, OpCode.IF_TRUE, OpCode.IF_FALSE, OpCode.TRY_BEGIN)
             and i.result is not None and labels.get(str(i.result.value), index + 1) <= index]
    changed = True
    while changed:
        changed = False
        for start, stop in loops:
            for span in spans.values():
                if span[1] < start <= span[2] < stop:
                    span[2] = stop
                    changed = True
    return spans


def _assign_temporaries(spans: Mapping[tuple[int, int], list], first: int):
    """Interval colouring over eight-byte cells: slots are reused after release."""
    cells: list[int] = []
    active: list[tuple[int, int]] = []
    placed: dict[tuple[int, int], int] = {}
    for lease, (_, start, stop) in sorted(spans.items(), key=lambda item: (item[1][1], item[0])):
        free = sorted(cell for end, cell in active if end < start)
        active = [(end, cell) for end, cell in active if end >= start]
        if free:
            cell = free[0]
        else:
            cell = len(cells)
            cells.append(first + SLOT_SIZE * cell)
        placed[lease] = cells[cell]
        active.append((stop, cell))
    return placed, first + SLOT_SIZE * len(cells)


def _frame_for(label: str, parameters: Sequence[Operand], instructions: Sequence[Instruction],
               abstract: ActivationRecordLayout, owners: dict) -> PhysicalFrame:
    hidden_names = [slot.name for slot in abstract.hidden_parameters]
    declared = len(abstract.parameters)
    if len(parameters) != len(hidden_names) + declared:
        raise MipsError('MIPS-MISSING-LAYOUT',
                        f'{label}: IR has {len(parameters)} parameters, layout {len(hidden_names) + declared}')
    arity = len(parameters)
    cursor = HEADER_SIZE
    local_cells: list[tuple[Symbol, int, int, int]] = []
    for slot in abstract.slots:
        if slot.kind in (FrameSlotKind.LOCAL, FrameSlotKind.CAPTURED) and slot.symbol is not None:
            cursor = align_up(cursor, slot.alignment)
            local_cells.append((slot.symbol, cursor, slot.size, memory_width(slot.symbol.type)))
            cursor += slot.size
    spans = _temporary_intervals(instructions)
    for lease in spans:
        if owners.setdefault(('lease', lease), label) != label:
            raise MipsError('MIPS-INVALID-IR', f'temporary lease {lease} is used by two procedures')
    placed, cursor = _assign_temporaries(spans, align_up(cursor, SLOT_SIZE))
    stage_count = max((i.arg2.value for i in instructions
                       if i.opcode in (OpCode.CALL, OpCode.CLOSURE_CALL)
                       and i.arg2 is not None and type(i.arg2.value) is int), default=0)
    staging_start = align_up(cursor, SLOT_SIZE)
    size = align_up(staging_start + SLOT_SIZE * stage_count, SLOT_SIZE)
    locals_ = {}
    for symbol, offset, cell, width in local_cells:
        if owners.setdefault(('symbol', id(symbol)), label) != label:
            raise MipsError('MIPS-INVALID-ADDRESS', f'symbol {symbol.name} appears in two frames')
        locals_[id(symbol)] = MachineLocation('$fp', offset, max(cell, width), width)
    temporaries = {lease: MachineLocation('$fp', placed[lease], SLOT_SIZE, memory_width(span[0]))
                   for lease, span in spans.items()}
    incoming = {}
    for index, parameter in enumerate(parameters):
        symbol = parameter.value.symbol
        if owners.setdefault(('symbol', id(symbol)), label) != label:
            raise MipsError('MIPS-INVALID-ADDRESS', f'symbol {symbol.name} appears in two frames')
        incoming[id(symbol)] = MachineLocation('$fp', size + SLOT_SIZE * index, SLOT_SIZE,
                                               abi_width(parameter.type))
    return PhysicalFrame(label, size, arity, incoming, locals_, temporaries, stage_count,
                         staging_start, 'env' in hidden_names)


def lexical_parents(layouts: object) -> dict[str, str]:
    """Label of the function lexically enclosing each frame, when scopes are known."""
    analysis = getattr(layouts, 'captures', None)
    parents: dict[str, str] = {}
    for scope in getattr(analysis, 'scopes', ()):
        if scope.kind is not ScopeKind.FUNCTION:
            continue
        outer = parent_function(scope)
        symbol, outer_symbol = function_symbol_of(scope), \
            function_symbol_of(outer) if outer is not None else None
        if symbol is None or outer_symbol is None:
            continue
        try:
            parents[layouts.frame_for(symbol).label] = layouts.frame_for(outer_symbol).label
        except LookupError:
            continue
    return parents


def mangle(label: str, used: set[str]) -> str:
    """Stable assembler name for a procedure label; never collides with ``main``."""
    base = 'proc_' + re.sub(r'[^A-Za-z0-9_]', '_', label)
    name, number = base, 2
    while name in used:
        name, number = f'{base}_{number}', number + 1
    used.add(name)
    return name


class PhysicalLayoutPlan:
    """All procedures are planned before any of them is emitted."""

    def __init__(self, frames: Mapping[str, PhysicalFrame],
                 signatures: Mapping[str, ProcedureSignature],
                 statics: Mapping[int, MachineLocation], static_size: int,
                 environments: Mapping[str, EnvironmentLayout],
                 parents: Mapping[str, str], classes: Mapping[str, ClassLayout],
                 owners: Mapping[tuple, str]) -> None:
        self.frames = MappingProxyType(dict(frames))
        self.signatures = MappingProxyType(dict(signatures))
        self.statics = MappingProxyType(dict(statics))
        self.static_size = align_up(static_size, SLOT_SIZE)
        self.environments = MappingProxyType(dict(environments))
        self.parents = MappingProxyType(dict(parents))
        self.classes = MappingProxyType(dict(classes))
        self._owners = dict(owners)
        used: set[str] = set()
        self.entry_labels = MappingProxyType({label: mangle(label, used) for label in self.signatures})

    @classmethod
    def build(cls, program: IRProgram, layouts: object, *,
              parents: Mapping[str, str] | None = None) -> 'PhysicalLayoutPlan':
        owners: dict = {}
        signatures = {str(p.label.value): signature_of(p) for p in program.procedures}
        if len(signatures) != len(program.procedures):
            raise MipsError('MIPS-INVALID-IR', 'duplicate procedure label')
        try:
            frames = {GLOBAL_UNIT: _frame_for(GLOBAL_UNIT, (), program.global_code,
                                              layouts.global_frame, owners)}
            environments = {}
            for procedure in program.procedures:
                label = str(procedure.label.value)
                abstract = layouts.frame_by_label(label)
                frames[label] = _frame_for(label, procedure.parameters, procedure.instructions,
                                           abstract, owners)
                if abstract.environment is not None:
                    environments[label] = abstract.environment
        except LookupError as error:
            raise MipsError('MIPS-MISSING-LAYOUT', str(error)) from error
        statics = {}
        for entry in layouts.symbols.by_storage(StorageClass.STATIC):
            if entry.offset is None:
                continue
            width = memory_width(entry.symbol.type)
            statics[id(entry.symbol)] = MachineLocation('$gp', entry.offset, max(entry.size, width), width)
        derived = dict(lexical_parents(layouts))
        derived.update(parents or {})
        plan = cls(frames, signatures, statics, layouts.symbols.static_size, environments,
                   derived, layouts.classes, owners)
        validate_locations(list(plan.statics.values()))
        return plan

    # -- LocationResolver -----------------------------------------------------------

    def frame(self, procedure: str) -> PhysicalFrame:
        try:
            return self.frames[procedure]
        except KeyError:
            raise LookupError(f'no physical frame for {procedure}') from None

    def signature(self, label: str) -> ProcedureSignature:
        try:
            return self.signatures[label]
        except KeyError:
            raise LookupError(f'unknown procedure {label}') from None

    def address_of(self, symbol: Symbol, procedure: str) -> MachineLocation:
        key = id(symbol)
        if key in self.statics:
            return self.statics[key]
        frame = self.frame(procedure)
        for table in (frame.parameters, frame.locals):
            if key in table:
                return table[key]
        owner = self._owners.get(('symbol', key))
        if owner is not None:
            raise MipsError('MIPS-INVALID-ADDRESS',
                            f"symbol '{symbol.name}' belongs to the frame of {owner}, not {procedure}")
        raise LookupError(f"no location for symbol '{symbol.name}' in {procedure}")

    def temporary_slot(self, lease: tuple[int, int], procedure: str) -> MachineLocation:
        frame = self.frame(procedure)
        if lease in frame.temporaries:
            return frame.temporaries[lease]
        owner = self._owners.get(('lease', lease))
        if owner is not None:
            raise MipsError('MIPS-INVALID-ADDRESS', f'lease {lease} belongs to {owner}, not {procedure}')
        raise LookupError(f'lease {lease} is not planned in {procedure}')

    def field_offset(self, owner: object, abstract_offset: int) -> int:
        """Instance offsets are preserved; only their validity is checked."""
        layout = owner
        if not isinstance(owner, ClassLayout):
            name = owner.name if isinstance(owner, (ClassType, Symbol)) else str(owner)
            layout = next((c for c in self.classes.values()
                           if c.label == name or c.symbol.name == name), None)
            if layout is None:
                raise LookupError(f'no class layout for {name}')
        if type(abstract_offset) is not int or abstract_offset < 0 or abstract_offset % 4 \
                or abstract_offset >= layout.size:
            raise MipsError('MIPS-INVALID-ADDRESS',
                            f'offset {abstract_offset} is outside class {layout.label}')
        return abstract_offset

    def environment_access(self, owner: object, depth: int, offset: int) -> EnvironmentAccess:
        label = owner.label if isinstance(owner, ActivationRecordLayout) else str(owner)
        if type(depth) is not int or depth < 0 or type(offset) is not int or offset < 0:
            raise MipsError('MIPS-INVALID-ADDRESS', f'invalid lexical access ({depth}, {offset})')
        if label != GLOBAL_UNIT and not self.frame(label).has_env:
            raise MipsError('MIPS-MISSING-LAYOUT', f'{label} receives no environment')
        level = self.parents.get(label)
        if level is None:
            raise MipsError('MIPS-MISSING-LAYOUT', f'{label} has no lexical parent')
        links: list[int] = []
        for _ in range(depth):
            environment = self.environments.get(level)
            if environment is None:
                raise MipsError('MIPS-MISSING-LAYOUT', f'{level} has no environment to link through')
            links.append(environment.parent_offset)
            next_level = self.parents.get(level)
            if next_level is None:
                raise MipsError('MIPS-MISSING-LAYOUT', f'access link from {level} does not exist')
            level = next_level
        environment = self.environments.get(level)
        if environment is None:
            raise MipsError('MIPS-MISSING-LAYOUT', f'{level} has no environment')
        if offset >= environment.size:
            raise MipsError('MIPS-INVALID-ADDRESS',
                            f'offset {offset} is outside the environment of {level}')
        return EnvironmentAccess(label, depth, tuple(links), offset, level)

    def entry_label(self, label: str) -> str:
        try:
            return self.entry_labels[label]
        except KeyError:
            raise MipsError('MIPS-UNKNOWN-EXTERNAL', f'no procedure labelled {label}') from None

"""Local register descriptors with pinned operands and typed memory backing."""
from __future__ import annotations

from src.codegen.contracts import Address
from src.codegen.ir import Operand, OperandKind
from src.mips.diagnostics import MipsError
from src.mips.emitter import MipsEmitter
from src.mips.models import LocationResolver, MachineLocation
from src.semantic.types import BOOLEAN, FLOAT, INTEGER, NULL, Type

SAVED_REGISTERS = tuple(f'$s{i}' for i in range(8))


def value_key(value: Operand, procedure: str) -> tuple:
    if value.kind is OperandKind.TEMPORARY:
        return procedure, 'temporary', value.lease
    if value.kind is OperandKind.SYMBOL and isinstance(value.value, Address):
        return procedure, 'symbol', id(value.value.symbol)
    if value.kind is OperandKind.CONSTANT:
        return procedure, 'constant', value.type, repr(value.value)
    raise MipsError('MIPS-INVALID-OPERAND', 'expected a typed value operand')


class RegisterAllocator:
    """Dirty values always have a resolver-owned spill destination.

    getReg does not unpin or silently evict an instruction's source operands.
    The scalar handler computes into reserved scratch before committing writes.

    Banks: temporaries and statics use ``$t``; a procedure's own variables
    (frame-resident symbols) use the callee-saved ``saved`` registers, which the
    calling convention preserves in the prologue/epilogue; doubles use ``$f``.
    """
    def __init__(self, emitter: MipsEmitter, locations: LocationResolver,
                 procedure: str = 'global', *, gpr_count: int = 8, fpr_count: int = 5,
                 saved: tuple[str, ...] = ()) -> None:
        if not 2 <= gpr_count <= 8 or not 2 <= fpr_count <= 5:
            raise ValueError('banks require 2..8 integer and 2..5 double registers')
        if any(register not in SAVED_REGISTERS for register in saved):
            raise ValueError('the saved bank only holds $s0..$s7')
        self.emitter, self.locations, self.procedure = emitter, locations, procedure
        self.gprs = tuple(f'$t{i}' for i in range(gpr_count))
        self.saved = tuple(saved)
        self.fprs = tuple(f'$f{i}' for i in range(2, 2 + 2 * fpr_count, 2))
        self.values: dict[tuple, tuple[str, Operand]] = {}
        self.dirty: set[tuple] = set()
        self.pinned: set[tuple] = set()
        self.released: set[tuple] = set()
        self._types: dict[tuple, Type] = {}
        self._defined: set[tuple] = set()
        self.spills = self.reloads = 0

    def _key(self, value: Operand) -> tuple:
        key = value_key(value, self.procedure)
        if key in self.released:
            raise MipsError('MIPS-TEMPORARY-RELEASED', str(value.value))
        if key in self._types and self._types[key] != value.type:
            raise MipsError('MIPS-TYPE', 'a value identity cannot change its machine type')
        if value.kind is OperandKind.SYMBOL and value.type != value.value.symbol.type:
            raise MipsError('MIPS-TYPE', 'operand type differs from its declaration')
        self._types[key] = value.type
        return key

    def location(self, value: Operand) -> MachineLocation:
        try:
            if value.kind is OperandKind.TEMPORARY:
                location = self.locations.temporary_slot(value.lease, self.procedure)
            elif value.kind is OperandKind.SYMBOL and isinstance(value.value, Address):
                if value.value.scope not in (None, self.procedure) and value.value.storage != 'static':
                    raise MipsError('MIPS-INVALID-ADDRESS', 'direct access to another frame')
                location = self.locations.address_of(value.value.symbol, self.procedure)
            else:
                raise MipsError('MIPS-MISSING-LAYOUT', 'operand has no storage')
        except LookupError as error:
            raise MipsError('MIPS-MISSING-LAYOUT', str(error)) from error
        expected = 8 if value.type == FLOAT else 1 if value.type == BOOLEAN else 4
        # Boolean ABI slots may intentionally transport a full word.
        if location.width != expected and not (value.type == BOOLEAN and location.width == 4):
            raise MipsError('MIPS-INVALID-ADDRESS', 'access width disagrees with value type')
        return location

    def getReg(self, value: Operand, mode: str = 'read', pinned: bool = False) -> str:
        if mode not in ('read', 'write'):
            raise ValueError('mode must be read or write')
        if mode == 'write' and value.kind is OperandKind.CONSTANT:
            raise MipsError('MIPS-INVALID-OPERAND', 'cannot write constant')
        key = self._key(value)
        if mode == 'read' and value.kind is OperandKind.TEMPORARY and key not in self._defined:
            raise MipsError('MIPS-TEMPORARY-UNDEFINED', str(value.value))
        if key not in self.values:
            bank = self._bank(value)
            used = {reg for reg, _ in self.values.values()}
            register = next((r for r in bank if r not in used), None)
            if register is None:
                victim = next((k for k, (r, _) in self.values.items()
                               if r in bank and k not in self.pinned), None)
                if victim is None:
                    raise MipsError('MIPS-REGISTERS-PINNED', 'no evictable register')
                register = self.values[victim][0]
                self._save(victim)
                del self.values[victim]
            self.values[key] = register, value
            if mode == 'read':
                if value.kind is OperandKind.CONSTANT:
                    self._constant(register, value)
                else:
                    self.emitter.load(register, self.location(value))
                    self.reloads += 1
        if mode == 'write':
            self.dirty.add(key)
            self._defined.add(key)
        if pinned:
            self.pinned.add(key)
        return self.values[key][0]

    def _bank(self, value: Operand) -> tuple[str, ...]:
        if value.type == FLOAT:
            return self.fprs
        if self.saved and value.kind is OperandKind.SYMBOL and self.location(value).base == '$fp':
            return self.saved
        return self.gprs

    def _constant(self, register: str, value: Operand) -> None:
        if value.type == FLOAT:
            if type(value.value) not in (int, float):
                raise MipsError('MIPS-TYPE', 'double literal must be numeric')
            try:
                literal = float(value.value)
            except OverflowError as error:
                raise MipsError('MIPS-TYPE', 'literal cannot be represented as double') from error
            self.emitter.emit('l.d', register, self.emitter.double(literal))
        elif value.type in (INTEGER, BOOLEAN, NULL):
            if value.type == INTEGER and (type(value.value) is not int or not -2**31 <= value.value < 2**31):
                raise MipsError('MIPS-INTEGER-LITERAL-RANGE', str(value.value))
            if value.type == BOOLEAN and type(value.value) is not bool:
                raise MipsError('MIPS-TYPE', 'boolean literal must be boolean')
            if value.type == NULL and value.value is not None:
                raise MipsError('MIPS-TYPE', 'null literal must be None')
            number = 0 if value.value is None else int(value.value)
            self.emitter.emit('li', register, str(number))
        else:
            raise MipsError('MIPS-UNRESOLVED-TYPE', 'literal requires a runtime provider')

    def pin(self, value: Operand) -> None:
        self.pinned.add(self._key(value))

    def unpin(self, value: Operand) -> None:
        self.pinned.discard(value_key(value, self.procedure))

    def write(self, value: Operand, scratch: str) -> None:
        target = self.getReg(value, 'write')
        self.emitter.emit('mov.d' if value.type == FLOAT else 'move', target, scratch)

    def _save(self, key: tuple) -> None:
        if key in self.dirty:
            register, value = self.values[key]
            self.emitter.store(register, self.location(value))
            self.dirty.remove(key)
            self.spills += 1

    def flush(self) -> None:
        for key in tuple(self.values):
            self._save(key)

    def invalidate(self) -> None:
        if self.dirty or self.pinned:
            raise MipsError('MIPS-DIRTY-REGISTERS', 'flush and unpin before invalidating')
        self.values.clear()

    def release(self, value: Operand) -> None:
        if value.kind is not OperandKind.TEMPORARY:
            raise MipsError('MIPS-INVALID-OPERAND', 'only temporary leases can be released')
        key = self._key(value)
        if key not in self._defined:
            raise MipsError('MIPS-TEMPORARY-UNDEFINED', 'lease does not belong to this allocation')
        if key in self.pinned:
            raise MipsError('MIPS-REGISTERS-PINNED', 'cannot release pinned operand')
        self.values.pop(key, None)
        self.dirty.discard(key)
        self.released.add(key)

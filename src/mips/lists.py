"""List opcodes over the heap representation of ``DISENO_MIPS.md`` (block 3).

A list is a zeroed heap region: its length (a word) at offset 0, padding up
to 8 and the elements from offset 8 with a stride of 8 bytes.  Each element is
accessed with the width of its type (``lbu``/``sb`` booleans, ``lw``/``sw``
integers and references, ``l.d``/``s.d`` doubles); the rest of the slot is
padding.  Before every access the list is checked against ``null``
(``NULL_ACCESS``) and the index against ``0 <= i < length`` with one unsigned
comparison, so negative indexes are rejected too (``INDEX_OUT_OF_RANGE``).
"""
from __future__ import annotations

from src.codegen.ir import Instruction, OpCode, Operand, OperandKind
from src.mips.diagnostics import MipsError
from src.mips.layout import memory_width, representation
from src.mips.models import EmissionContext
from src.mips.runtime import guard
from src.semantic.types import FLOAT, INTEGER, UNKNOWN, ArrayType, Type

LIST_OPCODES = frozenset({OpCode.LIST_NEW, OpCode.LIST_SET, OpCode.LIST_GET, OpCode.LIST_LEN})
LIST_HEADER = 8
ELEMENT_STRIDE = 8
# allocate() accepts up to 0x3ffffff0 bytes; the default step limit is far lower.
MAX_ELEMENTS = (0x3ffffff0 - LIST_HEADER) // ELEMENT_STRIDE
LOAD = {1: 'lbu', 4: 'lw', 8: 'l.d'}
STORE = {1: 'sb', 4: 'sw', 8: 's.d'}


def element_type(list_type: Type | None, value_type: Type | None) -> Type | None:
    """The declared element type, or the value's type for an untyped list."""
    if isinstance(list_type, ArrayType) and list_type.element_type != UNKNOWN:
        return list_type.element_type
    return value_type


class ListHandler:
    """``InstructionHandler`` for ``LIST_NEW``, ``LIST_SET``, ``LIST_GET`` and ``LIST_LEN``."""

    def supports(self, opcode: OpCode) -> bool:
        return opcode in LIST_OPCODES

    def emit(self, instruction: Instruction, context: EmissionContext) -> None:
        try:
            handler = {OpCode.LIST_NEW: self._new, OpCode.LIST_SET: self._set,
                       OpCode.LIST_GET: self._get, OpCode.LIST_LEN: self._len}.get(instruction.opcode)
            if handler is None:
                raise MipsError('MIPS-UNSUPPORTED-OPCODE', instruction.opcode.value)
            handler(instruction, context)
        except MipsError as error:
            if error.diagnostic.location is None and instruction.source_location is not None:
                raise MipsError(error.diagnostic.code, error.diagnostic.message,
                                instruction.source_location) from error
            raise

    @staticmethod
    def _list_operand(operand: Operand | None) -> Operand:
        if operand is None or not (isinstance(operand.type, ArrayType) or operand.type == UNKNOWN):
            raise MipsError('MIPS-TYPE', 'list operation needs a list reference')
        return operand

    @staticmethod
    def _index_operand(operand: Operand | None) -> Operand:
        if operand is None or operand.type != INTEGER:
            raise MipsError('MIPS-TYPE', 'list index must be an integer')
        return operand

    @staticmethod
    def _width(list_operand: Operand, value: Operand) -> int:
        declared = element_type(list_operand.type, value.type)
        if representation(declared) != representation(value.type):
            raise MipsError('MIPS-TYPE', f'{value.type} is not stored as {declared}')
        return memory_width(declared)

    def _new(self, instruction: Instruction, context: EmissionContext) -> None:
        count, result = instruction.arg1, instruction.result
        if count is None or count.kind is not OperandKind.CONSTANT or type(count.value) is not int:
            raise MipsError('MIPS-INVALID-IR', 'LIST_NEW needs a constant element count')
        if not 0 <= count.value <= MAX_ELEMENTS:
            raise MipsError('MIPS-INVALID-ADDRESS', f'invalid list size {count.value}')
        if result is None or not isinstance(result.type, ArrayType):
            raise MipsError('MIPS-TYPE', 'LIST_NEW needs a list destination')
        out = context.emitter
        pointer = context.runtime.allocate(context, LIST_HEADER + ELEMENT_STRIDE * count.value)
        out.emit('li', '$t9', str(count.value))
        out.emit('sw', '$t9', f'0({pointer})')
        context.registers.write(result, pointer)

    def _checked_address(self, context: EmissionContext, base: str, index: str) -> str:
        """Null and bounds checks; leaves the element slot address minus 8 in ``$t8``."""
        out = context.emitter
        guard(context, 'bnez', (base,), 'NULL_ACCESS')
        out.emit('lw', '$t9', f'0({base})')
        out.emit('sltu', '$t9', index, '$t9')
        guard(context, 'bnez', ('$t9',), 'INDEX_OUT_OF_RANGE')
        out.emit('sll', '$t8', index, '3')
        out.emit('addu', '$t8', '$t8', base)
        return '$t8'

    def _set(self, instruction: Instruction, context: EmissionContext) -> None:
        items = self._list_operand(instruction.arg1)
        index = self._index_operand(instruction.arg2)
        value = instruction.result
        if value is None:
            raise MipsError('MIPS-INVALID-IR', 'LIST_SET needs a value')
        width = self._width(items, value)
        registers = context.registers
        base = registers.getReg(items, pinned=True)
        position = registers.getReg(index, pinned=True)
        address = self._checked_address(context, base, position)
        # The address now lives in reserved scratch: the value may evict the
        # list or the index, so three operands fit even a two-register bank.
        registers.unpin(items)
        registers.unpin(index)
        source = registers.getReg(value)
        context.emitter.emit(STORE[width], source, f'{LIST_HEADER}({address})')

    def _get(self, instruction: Instruction, context: EmissionContext) -> None:
        items = self._list_operand(instruction.arg1)
        index = self._index_operand(instruction.arg2)
        result = instruction.result
        if result is None:
            raise MipsError('MIPS-INVALID-IR', 'LIST_GET needs a destination')
        width = self._width(items, result)
        registers = context.registers
        base = registers.getReg(items, pinned=True)
        position = registers.getReg(index, pinned=True)
        address = self._checked_address(context, base, position)
        scratch = '$f14' if result.type == FLOAT else '$t9'
        context.emitter.emit(LOAD[width], scratch, f'{LIST_HEADER}({address})')
        registers.unpin(items)
        registers.unpin(index)
        registers.write(result, scratch)

    def _len(self, instruction: Instruction, context: EmissionContext) -> None:
        items = self._list_operand(instruction.arg1)
        result = instruction.result
        if result is None or result.type != INTEGER:
            raise MipsError('MIPS-TYPE', 'LIST_LEN produces an integer')
        registers = context.registers
        base = registers.getReg(items, pinned=True)
        guard(context, 'bnez', (base,), 'NULL_ACCESS')
        context.emitter.emit('lw', '$t9', f'0({base})')
        registers.unpin(items)
        registers.write(result, '$t9')

"""Instances and their fields (block 3).

``OBJECT_NEW label, size`` reserves a zeroed heap region of exactly the size of
the class's ``ClassLayout``; fields (inherited first) and the slots that keep
the defining environments of local classes stay at their abstract offsets.
The TAC already calls the constructor, which runs the field initializers base
first: ``OBJECT_NEW`` never runs them again.  Methods are resolved statically
by the TAC; this backend introduces no dynamic dispatch.

``FIELD_GET``/``FIELD_SET`` check the receiver against ``null``
(``NULL_ACCESS``) and validate the offset against the layout of the receiver's
*own* class (by identity, so two homonymous classes never share a layout).
"""
from __future__ import annotations

from src.codegen.ir import Instruction, OpCode, Operand, OperandKind
from src.codegen.layout import ClassLayout
from src.mips.diagnostics import MipsError
from src.mips.layout import PhysicalLayoutPlan, memory_width, representation
from src.mips.models import EmissionContext
from src.mips.runtime import guard
from src.semantic.types import FLOAT, ClassType

OBJECT_OPCODES = frozenset({OpCode.OBJECT_NEW, OpCode.FIELD_SET, OpCode.FIELD_GET})
LOAD = {1: 'lbu', 4: 'lw', 8: 'l.d'}
STORE = {1: 'sb', 4: 'sw', 8: 's.d'}


class ObjectHandler:
    """``InstructionHandler`` for ``OBJECT_NEW``, ``FIELD_SET`` and ``FIELD_GET``."""

    def __init__(self, plan: PhysicalLayoutPlan) -> None:
        self.plan = plan

    def supports(self, opcode: OpCode) -> bool:
        return opcode in OBJECT_OPCODES

    def emit(self, instruction: Instruction, context: EmissionContext) -> None:
        try:
            handler = {OpCode.OBJECT_NEW: self._new, OpCode.FIELD_SET: self._set,
                       OpCode.FIELD_GET: self._get}.get(instruction.opcode)
            if handler is None:
                raise MipsError('MIPS-UNSUPPORTED-OPCODE', instruction.opcode.value)
            handler(instruction, context)
        except MipsError as error:
            if error.diagnostic.location is None and instruction.source_location is not None:
                raise MipsError(error.diagnostic.code, error.diagnostic.message,
                                instruction.source_location) from error
            raise

    # -- layouts --------------------------------------------------------------------

    def class_layout(self, owner: ClassType) -> ClassLayout:
        """Nominal lookup: the layout whose class symbol *is* this type."""
        matches = [layout for layout in self.plan.classes.values() if layout.symbol.type is owner]
        if len(matches) != 1:
            raise MipsError('MIPS-MISSING-LAYOUT', f'no single class layout for {owner}')
        return matches[0]

    def _field(self, receiver: Operand | None, offset: Operand | None, value: Operand | None) -> int:
        """Validated byte offset of a field access; returns its machine width."""
        if receiver is None or not isinstance(receiver.type, ClassType):
            raise MipsError('MIPS-UNRESOLVED-TYPE', 'field access needs a class-typed receiver')
        if offset is None or offset.kind is not OperandKind.OFFSET or type(offset.value) is not int:
            raise MipsError('MIPS-INVALID-ADDRESS', 'field access needs a byte offset')
        if value is None or value.type is None:
            raise MipsError('MIPS-INVALID-IR', 'field access needs a typed value')
        layout = self.class_layout(receiver.type)
        width = memory_width(value.type)
        position = offset.value
        if position < 0 or position % width or position + width > layout.size:
            raise MipsError('MIPS-INVALID-ADDRESS',
                            f'offset {position} ({width} bytes) is outside class {layout.label}')
        return width

    # -- handlers -----------------------------------------------------------------

    def _new(self, instruction: Instruction, context: EmissionContext) -> None:
        label, size, result = instruction.quadruple[1:]
        if label is None or label.kind is not OperandKind.LABEL:
            raise MipsError('MIPS-INVALID-IR', 'OBJECT_NEW needs a class label')
        layout = self.plan.classes.get(str(label.value))
        if layout is None:
            raise MipsError('MIPS-MISSING-LAYOUT', f'no class layout labelled {label.value}')
        if size is None or size.kind is not OperandKind.CONSTANT or size.value != layout.size \
                or type(size.value) is not int:
            raise MipsError('MIPS-INVALID-IR',
                            f'OBJECT_NEW {layout.label} must reserve {layout.size} bytes')
        if result is None or not isinstance(result.type, ClassType) \
                or self.class_layout(result.type) is not layout:
            raise MipsError('MIPS-TYPE', f'OBJECT_NEW {layout.label} needs a destination of that class')
        pointer = context.runtime.allocate(context, layout.size)
        context.registers.write(result, pointer)

    def _get(self, instruction: Instruction, context: EmissionContext) -> None:
        receiver, offset, result = instruction.quadruple[1:]
        width = self._field(receiver, offset, result)
        registers, out = context.registers, context.emitter
        base = registers.getReg(receiver, pinned=True)
        guard(context, 'bnez', (base,), 'NULL_ACCESS')
        scratch = '$f14' if result.type == FLOAT else '$t9'
        out.emit(LOAD[width], scratch, f'{offset.value}({base})')
        registers.unpin(receiver)
        registers.write(result, scratch)

    def _set(self, instruction: Instruction, context: EmissionContext) -> None:
        receiver, offset, value = instruction.quadruple[1:]
        width = self._field(receiver, offset, value)
        if representation(value.type) == 'double' and width != 8:
            raise MipsError('MIPS-TYPE', 'double field needs eight bytes')
        registers, out = context.registers, context.emitter
        base = registers.getReg(receiver, pinned=True)
        source = registers.getReg(value, pinned=True)
        guard(context, 'bnez', (base,), 'NULL_ACCESS')
        out.emit(STORE[width], source, f'{offset.value}({base})')
        registers.unpin(receiver)
        registers.unpin(value)

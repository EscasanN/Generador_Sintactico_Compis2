"""Handler records and unwinding for ``try``/``catch`` (block 3).

``TRY_BEGIN catch`` pushes a 40-byte record onto the stack and makes it the
head of a chain kept in a global word of the runtime (never a hidden ``$s``):

======  ==========================================================
offset  contents
======  ==========================================================
0       previous record (link)
8       address of the catch code
16      ``$sp`` to restore (the value before the record was pushed)
24      ``$fp`` of the protected activation
32      ``$ra`` at installation
======  ==========================================================

``TRY_END`` retires the head exactly once and releases its stack space.  The
TAC already emits one ``TRY_END`` per abandoned scope before ``return``,
``break`` and ``continue``; the epilogue never retires a record again.

When a runtime error is raised (``CompiscriptRuntime.error``) the ``raise``
routine retires the head record, restores ``$sp``/``$fp``/``$ra`` from it
(discarding the frames and argument packages of abandoned calls), stores the
error string in a global payload word and jumps to the catch code.  ``CATCH``
copies that payload into the catch variable.  The catch label is a block
boundary, so it starts with empty register descriptors.
"""
from __future__ import annotations

from collections.abc import Callable

from src.codegen.ir import Instruction, OpCode, OperandKind
from src.mips.diagnostics import MipsError
from src.mips.models import EmissionContext
from src.semantic.types import STRING

EXCEPTION_OPCODES = frozenset({OpCode.TRY_BEGIN, OpCode.TRY_END, OpCode.CATCH})
HANDLER_RECORD_SIZE = 40
LINK_OFFSET, CATCH_OFFSET, SP_OFFSET, FP_OFFSET, RA_OFFSET = 0, 8, 16, 24, 32


class ExceptionHandler:
    """``InstructionHandler`` for ``TRY_BEGIN``, ``TRY_END`` and ``CATCH``.

    ``resolve_label(name, context)`` must return the assembler label that the
    ``LABEL`` handler marks for the IR label ``name`` in the current unit, so the
    record points at the real catch code.
    """

    def __init__(self, resolve_label: Callable[[str, EmissionContext], str]) -> None:
        self.resolve_label = resolve_label

    def supports(self, opcode: OpCode) -> bool:
        return opcode in EXCEPTION_OPCODES

    def emit(self, instruction: Instruction, context: EmissionContext) -> None:
        try:
            handler = {OpCode.TRY_BEGIN: self._begin, OpCode.TRY_END: self._end,
                       OpCode.CATCH: self._catch}.get(instruction.opcode)
            if handler is None:
                raise MipsError('MIPS-UNSUPPORTED-OPCODE', instruction.opcode.value)
            handler(instruction, context)
        except MipsError as error:
            if error.diagnostic.location is None and instruction.source_location is not None:
                raise MipsError(error.diagnostic.code, error.diagnostic.message,
                                instruction.source_location) from error
            raise

    @staticmethod
    def _barrier(context: EmissionContext) -> None:
        context.registers.flush()
        context.registers.invalidate()

    def _begin(self, instruction: Instruction, context: EmissionContext) -> None:
        target = instruction.result
        if target is None or target.kind is not OperandKind.LABEL:
            raise MipsError('MIPS-INVALID-IR', 'TRY_BEGIN needs a catch label')
        if not hasattr(context.runtime, 'handler_head'):
            raise MipsError('MIPS-INTERNAL', 'exceptions need the complete runtime')
        self._barrier(context)
        out = context.emitter
        catch = self.resolve_label(str(target.value), context)
        out.references.add(catch)
        head = context.runtime.handler_head(out)
        out.emit('addiu', '$sp', '$sp', str(-HANDLER_RECORD_SIZE))
        out.emit('la', '$t9', head)
        out.emit('lw', '$t8', '0($t9)')
        out.emit('sw', '$t8', f'{LINK_OFFSET}($sp)')
        out.emit('la', '$t8', catch)
        out.emit('sw', '$t8', f'{CATCH_OFFSET}($sp)')
        out.emit('addiu', '$t8', '$sp', str(HANDLER_RECORD_SIZE))
        out.emit('sw', '$t8', f'{SP_OFFSET}($sp)')
        out.emit('sw', '$fp', f'{FP_OFFSET}($sp)')
        out.emit('sw', '$ra', f'{RA_OFFSET}($sp)')
        out.emit('sw', '$zero', f'{LINK_OFFSET + 4}($sp)')
        out.emit('sw', '$sp', '0($t9)')

    def _end(self, instruction: Instruction, context: EmissionContext) -> None:
        if any(value is not None for value in instruction.quadruple[1:]):
            raise MipsError('MIPS-INVALID-IR', 'TRY_END takes no operands')
        self._barrier(context)
        out = context.emitter
        head = context.runtime.handler_head(out)
        out.emit('la', '$t9', head)
        out.emit('lw', '$t8', '0($t9)')
        out.emit('lw', '$t8', f'{LINK_OFFSET}($t8)')
        out.emit('sw', '$t8', '0($t9)')
        out.emit('addiu', '$sp', '$sp', str(HANDLER_RECORD_SIZE))

    def _catch(self, instruction: Instruction, context: EmissionContext) -> None:
        result = instruction.result
        if result is None or result.type != STRING:
            raise MipsError('MIPS-TYPE', 'CATCH stores the error string in a string variable')
        out = context.emitter
        out.emit('la', '$t9', context.runtime.error_payload(out))
        out.emit('lw', '$t9', '0($t9)')
        context.registers.write(result, '$t9')

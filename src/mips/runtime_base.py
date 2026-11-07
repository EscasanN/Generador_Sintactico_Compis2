"""Inline syscall providers; no dependency on block 2's procedure ABI."""
from src.codegen.ir import Instruction, Operand
from src.mips.models import EmissionContext
from src.semantic.types import BOOLEAN, FLOAT, INTEGER, NULL
from src.mips.diagnostics import MipsError


class BaseRuntime:
    def emit_string(self, instruction: Instruction, context: EmissionContext) -> bool:
        """Return True only after emitting the complete string operation.

        Block 3 supplies its string representation and handlers here; absence
        is a rejection, never silent numeric lowering of a string address.
        """
        return False

    def exit(self, context: EmissionContext, code: int) -> None:
        out = context.emitter
        out.emit('li', '$a0', str(code))
        out.emit('li', '$v0', '17')
        out.emit('syscall')

    def error(self, context: EmissionContext, code: str) -> None:
        """Emit a non-returning error path with raw/reserved-register assembly.

        The caller has already flushed all dirty descriptors on both paths.
        Do not mutate/pin/invalidate the allocator here: its descriptors also
        describe the successful branch. Block 3 may emit a jump to its handler
        machinery using reserved scratch, with an empty cache at catch entry.
        """
        out = context.emitter
        out.emit('la', '$a0', out.ascii(f'RuntimeError: {code}\n'))
        out.emit('li', '$v0', '4')
        out.emit('syscall')
        self.exit(context, 1)

    def print_value(self, context: EmissionContext, value: Operand) -> None:
        registers, out = context.registers, context.emitter
        registers.flush()
        register = registers.getReg(value)
        if value.type == FLOAT:
            out.emit('mov.d', '$f12', register)
            out.emit('li', '$v0', '3')
        elif value.type == INTEGER:
            out.emit('move', '$a0', register)
            out.emit('li', '$v0', '1')
        elif value.type == BOOLEAN:
            false, end = out.label('false'), out.label('printed_bool')
            out.branch('beqz', false, register)
            out.emit('la', '$a0', out.ascii('true'))
            out.branch('b', end)
            out.mark(false)
            out.emit('la', '$a0', out.ascii('false'))
            out.mark(end)
            out.emit('li', '$v0', '4')
        elif value.type == NULL:
            out.emit('la', '$a0', out.ascii('null'))
            out.emit('li', '$v0', '4')
        else:
            raise MipsError('MIPS-UNRESOLVED-TYPE', 'print requires runtime provider')
        out.emit('syscall')
        out.emit('li', '$a0', '10')
        out.emit('li', '$v0', '11')
        out.emit('syscall')
        registers.invalidate()

    def allocate(self, context: EmissionContext, size: int) -> str:
        """Reserve aligned zeroed bytes; returns scratch $t8, consumed before next emission."""
        if type(size) is not int or not 0 <= size <= 0x3ffffff0:
            raise MipsError('MIPS-INVALID-ADDRESS', 'invalid heap reservation')
        registers, out = context.registers, context.emitter
        registers.flush()
        registers.invalidate()
        rounded = (size + 7) & -8  # cleared by doubleword, so the reservation must cover it
        out.emit('li', '$a0', str(rounded + 7))
        out.emit('li', '$v0', '9')
        out.emit('syscall')
        out.emit('addiu', '$t8', '$v0', '7')
        out.emit('li', '$t9', '-8')
        out.emit('and', '$t8', '$t8', '$t9')
        out.emit('move', '$a0', '$t8')
        out.emit('li', '$a1', str(rounded))
        loop, end = out.label('zero_heap'), out.label('heap_done')
        out.mark(loop)
        out.branch('beqz', end, '$a1')
        out.emit('sw', '$zero', '0($a0)')
        out.emit('sw', '$zero', '4($a0)')
        out.emit('addiu', '$a0', '$a0', '8')
        out.emit('addiu', '$a1', '$a1', '-8')
        out.branch('b', loop)
        out.mark(end)
        return '$t8'

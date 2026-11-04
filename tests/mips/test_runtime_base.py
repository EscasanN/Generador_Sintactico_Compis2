"""Base heap provider is aligned, zeroes its full reservation and keeps state."""
import pytest


def test_heap_provider_aligns_and_clears_memory(execute_scalar):
    from src.mips.runtime_base import BaseRuntime

    class HeapProbeRuntime(BaseRuntime):
        def exit(self, context, code):
            if code == 0:
                pointer = self.allocate(context, 17)
                out = context.emitter
                out.emit('andi', '$a0', pointer, '7')
                out.emit('li', '$v0', '1')
                out.emit('syscall')
                out.emit('lw', '$a0', f'0({pointer})')
                out.emit('syscall')
                out.emit('lbu', '$a0', f'16({pointer})')
                out.emit('syscall')
            super().exit(context, code)

    lines, _ = execute_scalar([], runtime=HeapProbeRuntime())
    assert lines == ['000']


@pytest.mark.parametrize('size', [-1, True, 2**31])
def test_invalid_heap_reservation_is_rejected(compile_scalar, size):
    from src.mips.runtime_base import BaseRuntime
    from src.mips.diagnostics import MipsError

    class InvalidHeapRuntime(BaseRuntime):
        def exit(self, context, code):
            self.allocate(context, size)

    with pytest.raises(MipsError, match='INVALID-ADDRESS'):
        compile_scalar([], runtime=InvalidHeapRuntime())


def test_heap_reservations_are_distinct_and_preserve_live_values(execute_scalar):
    from conftest import ins, constant as c, temporary as t
    from src.codegen.ir import OpCode as O
    from src.mips.runtime_base import BaseRuntime
    live = t(0)

    class TwoAllocations(BaseRuntime):
        def exit(self, context, code):
            if code == 0:
                out = context.emitter
                first = self.allocate(context, 17)
                out.emit('sw', first, '0($fp)')
                out.emit('li', '$t9', '77')
                out.emit('sb', '$t9', f'16({first})')
                second = self.allocate(context, 9)
                out.emit('lw', '$t9', '0($fp)')
                out.emit('sne', '$a0', second, '$t9')
                out.emit('li', '$v0', '1')
                out.emit('syscall')
                out.emit('lbu', '$a0', '16($t9)')
                out.emit('syscall')
                out.emit('lbu', '$a0', f'8({second})')
                out.emit('syscall')
                out.emit('move', '$a0', context.registers.getReg(live))
                out.emit('syscall')
            super().exit(context, code)

    lines, _ = execute_scalar([ins(O.COPY, c(41), result=live)], runtime=TwoAllocations())
    assert lines == ['177041']

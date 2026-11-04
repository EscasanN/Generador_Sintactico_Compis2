"""REG-*: spills and lease identity are verified by execution."""
import pytest

from conftest import constant as c, ins, temporary as t
from src.codegen.ir import OpCode as O
from src.semantic.types import FLOAT, INTEGER


def test_reg_01_allocation_and_pinning(execute_scalar):
    a, b, result = t(0), t(1), t(2)
    lines, _ = execute_scalar([ins(O.ADD, c(2), c(3), a), ins(O.SUB, c(7), c(1), b),
                               ins(O.MUL, a, b, result)], [result], gpr_count=2)
    assert lines == ['30']


@pytest.mark.parametrize('type_', [INTEGER, FLOAT])
def test_reg_02_spill_and_reload(execute_scalar, type_):
    values = [t(i, type_) for i in range(12)]
    result = t(12, type_)
    program = [ins(O.COPY, c(i + 1, type_), result=v) for i, v in enumerate(values)]
    program += [ins(O.COPY, c(0, type_), result=result)]
    program += [ins(O.ADD, result, v, result) for v in values]
    lines, registers = execute_scalar(program, [result], gpr_count=2, fpr_count=2)
    assert float(lines[0]) == 78
    assert registers.spills > 0 and registers.reloads > 0


def test_reg_03_temporary_leases(execute_scalar, compile_scalar):
    from src.mips.diagnostics import MipsError
    first, second = t(0, name='t0'), t(99, name='t0')
    program = [ins(O.COPY, c(3), result=first), ins(O.RELEASE, first),
               ins(O.COPY, c(9), result=second)]
    lines, _ = execute_scalar(program, [second])
    assert lines == ['9']
    with pytest.raises(MipsError):
        compile_scalar(program + [ins(O.ADD, first, c(1), second)])


def test_live_values_survive_successful_division(execute_scalar):
    a, b, quotient, result = t(0), t(1), t(2), t(3)
    program = [ins(O.COPY, c(41), result=a), ins(O.COPY, c(7), result=b),
               ins(O.DIV, a, b, quotient), ins(O.ADD, a, b, result),
               ins(O.ADD, result, quotient, result)]
    lines, _ = execute_scalar(program, [result], gpr_count=2)
    assert lines == ['53']


def test_pinned_operands_are_not_silently_evicted():
    from conftest import SlotResolver
    from src.mips.emitter import MipsEmitter
    from src.mips.registers import RegisterAllocator
    from src.mips.diagnostics import MipsError
    values = [t(i) for i in range(3)]
    allocator = RegisterAllocator(MipsEmitter(), SlotResolver(values), gpr_count=2)
    for value in values[:2]:
        allocator.getReg(value, 'write', pinned=True)
    with pytest.raises(MipsError, match='PINNED'):
        allocator.getReg(values[2], 'write')
    with pytest.raises(MipsError, match='DIRTY'):
        allocator.invalidate()
    allocator.unpin(values[0])
    allocator.getReg(values[2], 'write')
    assert allocator.spills == 1


def test_lease_cannot_change_type_after_definition(compile_scalar):
    from src.mips.diagnostics import MipsError
    integer = t(0)
    forged_double = t(0, FLOAT)
    with pytest.raises(MipsError, match='TYPE'):
        compile_scalar([ins(O.COPY, c(7), result=integer),
                        ins(O.COPY, forged_double, result=t(1, FLOAT))])


def test_foreign_lease_cannot_be_released():
    from conftest import SlotResolver
    from src.mips.emitter import MipsEmitter
    from src.mips.registers import RegisterAllocator
    from src.mips.diagnostics import MipsError
    value = t(0)
    allocator = RegisterAllocator(MipsEmitter(), SlotResolver([value]))
    with pytest.raises(MipsError, match='UNDEFINED'):
        allocator.release(value)


def test_disjoint_leases_can_reuse_one_slot_with_different_types(execute_scalar):
    from conftest import SlotResolver, symbol
    from src.mips.models import MachineLocation

    class CoalescedResolver(SlotResolver):
        def temporary_slot(self, lease, procedure):
            original = super().temporary_slot(lease, procedure)
            return MachineLocation('$fp', 32, 8, original.width)

    first, second, third = t(0, name='t0'), t(1, FLOAT, 't0'), t(2, name='t0')
    kept_int, kept_float = symbol('integer'), symbol('double', FLOAT)
    program = [ins(O.COPY, c(7), result=first), ins(O.COPY, first, result=kept_int),
               ins(O.RELEASE, first), ins(O.COPY, c(2.5, FLOAT), result=second),
               ins(O.COPY, second, result=kept_float), ins(O.RELEASE, second),
               ins(O.COPY, c(9), result=third)]
    lines, _ = execute_scalar(program, [kept_int, kept_float, third], resolver_factory=CoalescedResolver)
    assert lines == ['7', '2.5', '9']

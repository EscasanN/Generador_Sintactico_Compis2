"""NUM-01 and FLOW-01: expected results derived independently of backend."""
import math

import pytest

from conftest import constant as c, ins, symbol, temporary as t
from src.codegen.ir import OpCode as O, Operand, OperandKind
from src.semantic.types import BOOLEAN, FLOAT, INTEGER


@pytest.mark.parametrize('op,a,b,want', [
    (O.ADD, 7, 2, 9), (O.SUB, 7, 2, 5), (O.MUL, -7, 2, -14),
    (O.DIV, -7, 2, -3), (O.MOD, -7, 2, -1), (O.MOD, 7, -2, 1),
    (O.ADD, 2147483647, 1, -2147483648),
    (O.DIV, -2147483648, -1, -2147483648), (O.MOD, -2147483648, -1, 0),
    (O.EQ, 4, 4, 1), (O.NE, 4, 4, 0), (O.LT, 4, 5, 1),
    (O.LE, 4, 4, 1), (O.GT, 5, 4, 1), (O.GE, 4, 5, 0),
])
def test_num_01_integer_operations(execute_scalar, op, a, b, want):
    result = t(0, BOOLEAN if op in {O.EQ, O.NE, O.LT, O.LE, O.GT, O.GE} else INTEGER)
    lines, _ = execute_scalar([ins(op, c(a), c(b), result)], [result])
    assert lines == ([str(bool(want)).lower()] if result.type == BOOLEAN else [str(want)])


@pytest.mark.parametrize('op,a,b,want', [
    (O.ADD, 1.25, 2.5, 3.75), (O.SUB, 1.25, 2.5, -1.25),
    (O.MUL, -1.25, 2.5, -3.125), (O.DIV, 7.0, 2.0, 3.5),
    (O.MOD, -7.5, 2.0, -1.5), (O.MOD, 1e20, 3.0, 1.0),
    (O.MOD, 1e308, 1e-308, 3.498445546245627e-309),
])
def test_num_01_double_operations(execute_scalar, op, a, b, want):
    result = t(0, FLOAT)
    lines, _ = execute_scalar([ins(op, c(a, FLOAT), c(b, FLOAT), result)], [result])
    assert math.isclose(float(lines[0]), want, rel_tol=1e-9, abs_tol=0.0)


@pytest.mark.parametrize('op,a,b,want', [(O.EQ, float('nan'), 1., False),
    (O.NE, float('nan'), 1., True), (O.LT, -2., 1., True),
    (O.LE, 1., 1., True), (O.GT, 2., 1., True), (O.GE, 1., 2., False)])
def test_num_01_double_comparisons(execute_scalar, op, a, b, want):
    result = t(0, BOOLEAN)
    lines, _ = execute_scalar([ins(op, c(a, FLOAT), c(b, FLOAT), result)], [result])
    assert lines == [str(want).lower()]


def test_num_01_unary_and_cast(execute_scalar):
    neg, logic, cast = t(0), t(1, BOOLEAN), t(2, FLOAT)
    target = Operand(OperandKind.LABEL, 'float')
    lines, _ = execute_scalar([ins(O.NEG, c(3), result=neg),
                              ins(O.NOT, c(False, BOOLEAN), result=logic),
                              ins(O.CAST, neg, target, cast)], [neg, logic, cast])
    assert lines == ['-3', 'true', '-3.0']


@pytest.mark.parametrize('op,type_', [(O.DIV, INTEGER), (O.MOD, INTEGER), (O.DIV, FLOAT), (O.MOD, FLOAT)])
def test_num_01_zero_error(compile_scalar, mars, op, type_):
    from src.mips.simulator import run_mars
    result = t(0, type_)
    asm, _ = compile_scalar([ins(op, c(3, type_), c(0, type_), result)], [result])
    run = run_mars(asm, mars)
    assert run.status == 'runtime_error' and run.returncode == 1
    assert run.stdout == 'RuntimeError: DIV_ZERO\n'


def test_num_01_operations_and_errors(compile_scalar):
    from src.mips.diagnostics import MipsError
    with pytest.raises(MipsError, match='RANGE'):
        compile_scalar([ins(O.COPY, c(2147483648), result=t(0))])
    with pytest.raises(MipsError, match='TYPE'):
        compile_scalar([ins(O.ADD, c(True, BOOLEAN), c(3), t(0))])
    with pytest.raises(MipsError, match='UNSUPPORTED'):
        compile_scalar([ins(O.LIST_NEW, c(0), result=t(0))])


def test_flow_01_joins_and_loops(execute_scalar):
    counter, total, condition = symbol('counter'), symbol('total'), t(0, BOOLEAN)
    loop, end = Operand(OperandKind.LABEL, 'loop'), Operand(OperandKind.LABEL, 'end')
    program = [ins(O.COPY, c(0), result=counter), ins(O.COPY, c(0), result=total),
        ins(O.LABEL, result=loop), ins(O.LT, counter, c(5), condition),
        ins(O.IF_FALSE, condition, result=end), ins(O.ADD, total, counter, total),
        ins(O.ADD, counter, c(1), counter), ins(O.GOTO, result=loop),
        ins(O.LABEL, result=end)]
    lines, _ = execute_scalar(program, [total, counter], gpr_count=2)
    assert lines == ['10', '5']


@pytest.mark.parametrize('a,b,want', [(0., 2., 0.), (-0., 2., -0.),
    (float('inf'), 2., float('nan')), (1., float('inf'), 1.),
    (1., float('nan'), float('nan'))])
def test_double_remainder_special_values(execute_scalar, a, b, want):
    value = t(0, FLOAT)
    lines, _ = execute_scalar([ins(O.MOD, c(a, FLOAT), c(b, FLOAT), value)], [value])
    actual = float(lines[0])
    if math.isnan(want):
        assert math.isnan(actual)
    else:
        assert actual == want and math.copysign(1, actual) == math.copysign(1, want)


def test_reference_copy_preserves_nominal_subtyping(execute_scalar):
    from src.semantic.types import ClassType, NULL
    base = ClassType('Base')
    child = ClassType('Child', base)
    source, destination, same = symbol('child', child), symbol('base', base), t(0, BOOLEAN)
    program = [ins(O.COPY, c(None, NULL), result=source),
               ins(O.COPY, source, result=destination), ins(O.EQ, source, destination, same)]
    lines, _ = execute_scalar(program, [same])
    assert lines == ['true']


def test_string_provider_can_extend_numeric_handler(execute_scalar):
    from src.mips.runtime_base import BaseRuntime
    from src.semantic.types import STRING

    class LiteralStringRuntime(BaseRuntime):
        """An actual tiny provider for literal concatenation, not a full string runtime."""
        def emit_string(self, instruction, context):
            if instruction.opcode is not O.ADD:
                return False
            text = instruction.arg1.value + instruction.arg2.value
            out = context.emitter
            out.emit('la', '$t8', out.ascii(text))
            context.registers.write(instruction.result, '$t8')
            return True

        def print_value(self, context, value):
            if value.type != STRING:
                return super().print_value(context, value)
            reg = context.registers.getReg(value)
            context.emitter.emit('move', '$a0', reg)
            context.emitter.emit('li', '$v0', '4')
            context.emitter.emit('syscall')

    result = t(0, STRING)
    program = [ins(O.ADD, c('Compi', STRING), c('script', STRING), result)]
    lines, _ = execute_scalar(program, [result], runtime=LiteralStringRuntime())
    assert lines == ['Compiscript']


@pytest.mark.parametrize('value,type_', [
    ('not-a-number', INTEGER), ('false', BOOLEAN), (123, None), (10**400, FLOAT),
])
def test_invalid_literal_has_located_backend_diagnostic(compile_scalar, value, type_):
    from src.mips.diagnostics import MipsError
    from src.semantic.types import NULL
    type_ = NULL if type_ is None else type_
    with pytest.raises(MipsError) as caught:
        compile_scalar([ins(O.COPY, c(value, type_), result=t(0, type_))])
    assert caught.value.diagnostic.location.line == 1


def test_labels_are_not_shared_when_an_emitter_id_is_recycled(monkeypatch):
    from types import SimpleNamespace
    from src.mips.emitter import MipsEmitter
    from src.mips.scalar import ScalarLowerer
    monkeypatch.setattr('src.mips.scalar.id', lambda _: 0, raising=False)
    lowerer = ScalarLowerer()
    first, second = MipsEmitter(), MipsEmitter()
    first.label('shifts the serial')
    name = lowerer._label('end', SimpleNamespace(emitter=first, procedure='global'))
    assert lowerer._label('end', SimpleNamespace(emitter=second, procedure='global')) != name

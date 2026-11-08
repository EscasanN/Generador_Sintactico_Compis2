"""CALL-01..CALL-04: the ABI executed in MARS with manual typed IR.

Oracles are literals computed by hand, never produced by the backend.
"""
import pytest

from abi_harness import (
    NULL_CONSTANT, CanaryProbe, Model, assemble, const, execute, label, lines,
)
from src.codegen.ir import OpCode as O
from src.mips.diagnostics import MipsError
from src.semantic.types import BOOLEAN, FLOAT, INTEGER, ClassType

BOX = ClassType('Box')


def reject(model, code, **options):
    with pytest.raises(MipsError) as caught:
        assemble(model, **options)
    assert caught.value.diagnostic.code == code, caught.value
    return caught.value


# ---------------------------------------------------------------- CALL-01 arguments

def test_call_01_arguments(mars):
    m = Model()
    zero = m.procedure('zero')
    zero.ret(const(7))
    twice = m.procedure('twice', [('x', INTEGER)])
    twice.ret(twice.binary(O.MUL, twice.param('x'), const(2)))
    sum6 = m.procedure('sum6', [(n, INTEGER) for n in 'abcdef'])
    total = sum6.param('a')
    for name in 'bcdef':
        total = sum6.binary(O.ADD, total, sum6.param(name))
    sum6.ret(total)
    digits = m.procedure('digits', [(n, INTEGER) for n in 'abcdef'])
    acc = digits.param('a')
    for name in 'bcdef':
        acc = digits.binary(O.ADD, digits.binary(O.MUL, acc, const(10)), digits.param(name))
    digits.ret(acc)
    g = m.global_
    g.show(g.call('zero', [], INTEGER))
    g.show(g.call('twice', [const(21)], INTEGER))
    g.show(g.call('sum6', [const(n) for n in range(1, 7)], INTEGER))
    g.show(g.call('digits', [const(n) for n in range(1, 7)], INTEGER))
    assert lines(m, mars) == ['7', '42', '21', '123456']


def test_call_01_mixed_integer_double_boolean_reference(mars):
    m = Model()
    mixed = m.procedure('mixed', [('i', INTEGER), ('d', FLOAT), ('b', BOOLEAN), ('r', BOX), ('j', INTEGER)])
    for name in 'idb':
        mixed.show(mixed.param(name))
    mixed.show(mixed.binary(O.NE, mixed.param('r'), NULL_CONSTANT, BOOLEAN))
    mixed.show(mixed.param('j'))
    mixed.ret()
    g = m.global_
    box = g.tmp(BOX)
    g.emit(O.ENV_NEW, const(8), None, box)
    g.call('mixed', [const(5), const(2.5, FLOAT), const(True, BOOLEAN), box, const(-3)])
    g.call('mixed', [const(-1), const(-0.125, FLOAT), const(False, BOOLEAN), NULL_CONSTANT, const(8)])
    assert lines(m, mars) == ['5', '2.5', 'true', 'true', '-3', '-1', '-0.125', 'false', 'false', '8']


def test_call_01_arguments_are_captured_once_and_survive_release(mars):
    """The package holds values: neither a released lease nor a re-run call changes it."""
    m = Model()
    hits = m.static('hits', INTEGER)
    produce = m.procedure('produce')
    produce.copy(produce.binary(O.ADD, hits, const(1)), hits)
    produce.ret(const(41))
    consume = m.procedure('consume', [('x', INTEGER), ('y', INTEGER)])
    consume.show(consume.binary(O.ADD, consume.param('x'), consume.param('y')))
    consume.ret()
    g = m.global_
    first = g.call('produce', [], INTEGER, keep=True)
    second = g.binary(O.ADD, first, const(1))
    g.emit(O.PARAM, first)
    g.release(first)  # allowed between PARAM and CALL: the value was already staged
    g.emit(O.PARAM, second)
    g.emit(O.CALL, label('consume'), const(2))
    g.release(second)
    g.show(hits)
    assert lines(m, mars) == ['83', '1']


def test_call_01_rejects_bad_signatures():
    def callee(m, params):
        proc = m.procedure('f', params)
        proc.ret()
        return proc

    m = Model()
    callee(m, [('a', INTEGER), ('b', INTEGER)])
    m.global_.emit(O.PARAM, const(1))
    m.global_.emit(O.CALL, label('f'), const(1))
    assert reject(m, 'MIPS-INVALID-IR')  # arity differs from the signature

    m = Model()
    callee(m, [('a', FLOAT)])
    m.global_.call('f', [const(1)])
    assert 'argument 0' in reject(m, 'MIPS-CALL-SIGNATURE').diagnostic.message  # int into double

    m = Model()
    callee(m, [])
    m.global_.emit(O.PARAM, const(1))
    assert reject(m, 'MIPS-INVALID-IR')  # PARAM without its call

    m = Model()
    m.global_.call('nowhere', [const(1)])
    reject(m, 'MIPS-UNKNOWN-EXTERNAL')

    m = Model()
    m.global_.call('print', [const(1), const(2)])
    reject(m, 'MIPS-CALL-ARITY')

    m = Model()
    m.global_.call('print', [const(1)], INTEGER)  # print yields nothing to store
    assert 'returns no value' in reject(m, 'MIPS-CALL-SIGNATURE').diagnostic.message


# ---------------------------------------------------------------- CALL-02 returns

def test_call_02_returns(mars):
    m = Model()
    note = m.procedure('note')
    note.show(const(9))
    note.ret()
    forty_two = m.procedure('forty_two')
    forty_two.ret(const(42))
    half = m.procedure('half')
    half.ret(const(2.5, FLOAT))
    truth = m.procedure('truth')
    truth.ret(const(True, BOOLEAN))
    make = m.procedure('make')
    pointer = make.tmp(BOX)
    make.emit(O.ENV_NEW, const(16), None, pointer)
    make.ret(pointer)
    pick = m.procedure('pick', [('flag', BOOLEAN)])
    other = label('other')
    pick.emit(O.IF_FALSE, pick.param('flag'), None, other)
    pick.ret(const(1))
    pick.emit(O.LABEL, None, None, other)
    pick.ret(const(2))
    g = m.global_
    g.call('note')
    g.show(g.call('forty_two', [], INTEGER))
    g.show(g.call('half', [], FLOAT))
    g.show(g.call('truth', [], BOOLEAN))
    ref = g.call('make', [], BOX, keep=True)
    g.show(g.binary(O.NE, ref, NULL_CONSTANT, BOOLEAN))
    g.show(g.call('pick', [const(True, BOOLEAN)], INTEGER))
    g.show(g.call('pick', [const(False, BOOLEAN)], INTEGER))
    assert lines(m, mars) == ['9', '42', '2.5', 'true', 'true', '1', '2']


def test_call_02_rejects_incompatible_returns():
    m = Model()
    v = m.procedure('v')
    v.ret()
    m.global_.call('v', [], INTEGER)
    assert 'returns no value' in reject(m, 'MIPS-CALL-SIGNATURE').diagnostic.message

    m = Model()
    d = m.procedure('d')
    d.ret(const(1.5, FLOAT))
    m.global_.call('d', [], INTEGER)
    reject(m, 'MIPS-CALL-SIGNATURE')

    m = Model()
    mixed = m.procedure('mixed', [('f', BOOLEAN)])
    other = label('other')
    mixed.emit(O.IF_FALSE, mixed.param('f'), None, other)
    mixed.ret(const(1))
    mixed.emit(O.LABEL, None, None, other)
    mixed.ret(const(1.5, FLOAT))
    reject(m, 'MIPS-CALL-SIGNATURE')

    m = Model()
    m.global_.ret(const(1))
    reject(m, 'MIPS-INVALID-IR')


# ---------------------------------------------------------------- CALL-03 preservation

def test_call_03_preservation(mars):
    m = Model()
    shared = m.static('shared', INTEGER)
    ten = m.procedure('ten')
    ten.ret(const(10))
    twenty = m.procedure('twenty')
    twenty.ret(const(20))
    one_and_a_half = m.procedure('one_and_a_half')
    one_and_a_half.ret(const(1.5, FLOAT))
    two_and_a_quarter = m.procedure('two_and_a_quarter')
    two_and_a_quarter.ret(const(2.25, FLOAT))
    bump = m.procedure('bump')
    bump.copy(bump.binary(O.ADD, shared, const(1)), shared)
    bump.ret()
    scribble = m.procedure('scribble')
    cells = [scribble.local(f'c{i}', INTEGER) for i in range(12)]
    for cell in cells:
        scribble.copy(const(-1), cell)
    scribble.ret(const(0))
    wide = m.procedure('wide', [('a', INTEGER), ('b', INTEGER)])
    wide.ret(wide.binary(O.ADD, wide.param('a'), wide.param('b')))

    g = m.global_
    canary = g.local('canary', INTEGER)
    g.copy(const(0x1234567), canary)
    # f() + g(): the first result is live while the second call runs.
    first = g.call('ten', [], INTEGER, keep=True)
    second = g.call('twenty', [], INTEGER, keep=True)
    g.show(g.binary(O.ADD, first, second))
    g.release(first, second)
    # Doubles, also live across a call.
    d1 = g.call('one_and_a_half', [], FLOAT, keep=True)
    d2 = g.call('two_and_a_quarter', [], FLOAT, keep=True)
    g.show(g.binary(O.ADD, d1, d2, FLOAT))
    g.release(d1, d2)
    # Five operands live (more than the two registers available) around a call.
    live = []
    for number in range(1, 6):
        live.append(g.copy(const(number * 100), g.tmp()))
    ten_again = g.call('ten', [], INTEGER, keep=True)
    total = ten_again
    for item in live:
        total = g.binary(O.ADD, total, item)
    g.show(total)
    # A global written before, inside and after a call.
    g.copy(const(5), shared)
    g.call('bump')
    g.call('bump')
    g.show(shared)
    # Live operand around the print runtime helper and a heap allocation.
    kept = g.copy(const(40), g.tmp())
    g.show(const(0))
    pointer = g.tmp(BOX)
    g.emit(O.ENV_NEW, const(24), None, pointer)
    g.show(g.binary(O.ADD, kept, const(2)))
    # Callee frames never reach back into the caller frame.
    g.call('scribble', [], INTEGER)
    g.show(canary)
    g.show(g.call('wide', [g.binary(O.ADD, const(1), const(2)), const(4)], INTEGER))
    probe = CanaryProbe()
    result, assembly, _, emitter = execute(m, mars, gpr_count=2, fpr_count=2,
                                           before_global=probe.before, after_global=probe.after)
    assert result.accepted, (result.status, result.stdout, result.stderr[-400:])
    assert result.stdout.splitlines() == ['30', '3.75', '1510', '7', '0', '42', str(0x1234567), '7', '1']
    assert emitter.statistics['spills'] > 0 and emitter.statistics['reloads'] > 0


# ---------------------------------------------------------------- CALL-04 recursion

def build_recursive_model():
    m = Model()
    fact = m.procedure('fact', [('n', INTEGER)])
    recurse = label('recurse')
    fact.emit(O.IF_FALSE, fact.binary(O.LE, fact.param('n'), const(1), BOOLEAN), None, recurse)
    fact.ret(const(1))
    fact.emit(O.LABEL, None, None, recurse)
    smaller = fact.binary(O.SUB, fact.param('n'), const(1))
    inner = fact.call('fact', [smaller], INTEGER, keep=True)
    fact.ret(fact.binary(O.MUL, fact.param('n'), inner))

    fib = m.procedure('fib', [('n', INTEGER)])
    big = label('big')
    fib.emit(O.IF_FALSE, fib.binary(O.LT, fib.param('n'), const(2), BOOLEAN), None, big)
    fib.ret(fib.param('n'))
    fib.emit(O.LABEL, None, None, big)
    left = fib.call('fib', [fib.binary(O.SUB, fib.param('n'), const(1))], INTEGER, keep=True)
    right = fib.call('fib', [fib.binary(O.SUB, fib.param('n'), const(2))], INTEGER, keep=True)
    fib.ret(fib.binary(O.ADD, left, right))

    even = m.procedure('is_even', [('n', INTEGER)])
    even_more = label('even_more')
    even.emit(O.IF_FALSE, even.binary(O.EQ, even.param('n'), const(0), BOOLEAN), None, even_more)
    even.ret(const(True, BOOLEAN))
    even.emit(O.LABEL, None, None, even_more)
    even.ret(even.call('is_odd', [even.binary(O.SUB, even.param('n'), const(1))], BOOLEAN, keep=True))
    odd = m.procedure('is_odd', [('n', INTEGER)])
    odd_more = label('odd_more')
    odd.emit(O.IF_FALSE, odd.binary(O.EQ, odd.param('n'), const(0), BOOLEAN), None, odd_more)
    odd.ret(const(False, BOOLEAN))
    odd.emit(O.LABEL, None, None, odd_more)
    odd.ret(odd.call('is_even', [odd.binary(O.SUB, odd.param('n'), const(1))], BOOLEAN, keep=True))

    # Every activation keeps its own local and return address.
    total = m.procedure('total', [('n', INTEGER)])
    mine = total.local('mine', INTEGER)
    total.copy(total.param('n'), mine)
    stop = label('stop')
    total.emit(O.IF_FALSE, total.binary(O.GT, total.param('n'), const(0), BOOLEAN), None, stop)
    rest = total.call('total', [total.binary(O.SUB, total.param('n'), const(1))], INTEGER, keep=True)
    total.copy(total.binary(O.MUL, mine, const(1)), mine)
    total.ret(total.binary(O.ADD, mine, rest))
    total.emit(O.LABEL, None, None, stop)
    total.ret(const(0))
    return m


def test_call_04_recursion(mars):
    m = build_recursive_model()
    g = m.global_
    g.show(g.call('fact', [const(5)], INTEGER))
    g.show(g.call('fib', [const(8)], INTEGER))
    g.show(g.call('is_even', [const(10)], BOOLEAN))
    g.show(g.call('is_odd', [const(7)], BOOLEAN))
    g.show(g.call('is_even', [const(7)], BOOLEAN))
    g.show(g.call('total', [const(5)], INTEGER))
    g.show(g.call('total', [const(200)], INTEGER))
    probe = CanaryProbe()
    result, assembly, _, _ = execute(m, mars, before_global=probe.before, after_global=probe.after)
    assert result.accepted, (result.status, result.stdout, result.stderr[-400:])
    assert result.stdout.splitlines() == ['120', '21', 'true', 'true', 'false', '15', '20100', '1']


def test_call_04_recursion_with_scarce_registers(mars):
    m = build_recursive_model()
    g = m.global_
    g.show(g.call('fib', [const(10)], INTEGER))
    g.show(g.call('fact', [const(10)], INTEGER))
    assert lines(m, mars, gpr_count=2, fpr_count=2) == ['55', '3628800']


def test_call_01_argument_loader_hook_for_values_the_allocator_cannot_load(mars):
    """Block 3 materializes string literals; the call package only needs the register."""
    from src.semantic.types import STRING

    m = Model()
    echo = m.procedure('echo', [('s', STRING)])
    echo.ret(echo.param('s'))
    g = m.global_
    g.show(g.call('echo', [const('hola', STRING)], INTEGER))   # string and int share a word
    with pytest.raises(MipsError, match='UNRESOLVED-TYPE'):    # no provider: rejected, never faked
        assemble(m)

    def loader(operand, context):
        if operand.type == STRING:
            context.emitter.emit('li', '$t8', '99')            # a provider would `la` the literal
            return '$t8'
        return None

    assert lines(m, mars, loader=loader) == ['99']


def test_epilogues_are_not_shared_when_an_emitter_id_is_recycled(monkeypatch):
    from types import SimpleNamespace
    from src.mips.calls import CallingConvention
    from src.mips.emitter import MipsEmitter
    monkeypatch.setattr('src.mips.calls.id', lambda _: 0, raising=False)
    handler = CallingConvention(None)
    first, second = MipsEmitter(), MipsEmitter()
    first.label('shifts the serial')
    name = handler._epilogue(SimpleNamespace(emitter=first, procedure='f'))
    assert handler._epilogue(SimpleNamespace(emitter=second, procedure='f')) != name

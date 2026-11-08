"""ENV-01..ENV-03 and METHOD-01: environments, closures and bound methods in MARS.

Receivers are plain heap regions prepared by the harness, so nothing here needs
the object runtime of block 3.  Oracles are hand-computed literals.
"""
import pytest

from abi_harness import NULL_CONSTANT, Model, assemble, const, execute, label, lines, offset
from src.codegen.ir import OpCode as O
from src.mips.diagnostics import MipsError
from src.semantic.types import BOOLEAN, FLOAT, INTEGER, UNKNOWN, VOID, ClassType, FunctionType

BOX = ClassType('Box')
THUNK = FunctionType((), VOID)
COUNTER = FunctionType((), INTEGER)
UNARY = FunctionType((INTEGER,), INTEGER)


def get(proc, env, where, type_=INTEGER):
    return proc.emit(O.ENV_GET, env, offset(where), proc.tmp(type_))


def put(proc, env, where, value):
    proc.emit(O.ENV_SET, env, offset(where), value)


def new_env(proc, size, type_=UNKNOWN):
    return proc.emit(O.ENV_NEW, const(size), None, proc.tmp(type_))


def closure(proc, target, env, type_):
    return proc.emit(O.CLOSURE, label(target), env, proc.tmp(type_))


def reject(model, code):
    with pytest.raises(MipsError) as caught:
        assemble(model)
    assert caught.value.diagnostic.code == code, caught.value
    return caught.value


# ---------------------------------------------------------------- ENV-01 lexical access

def build_chain():
    """A -> B -> C -> D; every environment keeps its parent link at a different offset."""
    m = Model()
    env_a = Model.environment('A', [('a', INTEGER, 0)], 8, 16)
    env_b = Model.environment('B', [('b', INTEGER, 0), ('b2', INTEGER, 4)], 16, 24)
    env_c = Model.environment('C', [('c', INTEGER, 0)], 8, 16)
    a = m.procedure('A', environment=env_a)
    b = m.procedure('B', hidden=('env',), parent='A', environment=env_b)
    c = m.procedure('C', hidden=('env',), parent='B', environment=env_c)
    d = m.procedure('D', hidden=('env',), parent='C')

    ea = new_env(a, 16)
    put(a, ea, 0, const(1))
    call = closure(a, 'B', ea, THUNK)
    a.call_indirect(call)
    a.show(get(a, ea, 0))
    a.ret()

    eb = new_env(b, 24)
    put(b, eb, 16, b.param('env'))
    put(b, eb, 0, const(20))
    put(b, eb, 4, const(99))
    b.call_indirect(closure(b, 'C', eb, THUNK))
    b.show(get(b, eb, 0))
    b.show(get(b, eb, 4))
    b.ret()

    ec = new_env(c, 16)
    put(c, ec, 8, c.param('env'))
    put(c, ec, 0, const(300))
    c.call_indirect(closure(c, 'D', ec, THUNK))
    c.show(get(c, ec, 0))
    c.ret()

    env = d.param('env')
    for depth in (0, 1, 2):
        d.show(get(d, env, (depth, 0)))
    d.show(get(d, env, (1, 4)))
    put(d, env, (2, 0), const(11))
    put(d, env, (1, 0), const(22))
    put(d, env, (0, 0), const(333))
    d.ret()
    m.global_.call('A')
    return m


def test_env_01_lexical_links(mars):
    # Reads at depth 0, 1 and 2 hit the right declaration and writes land there.
    assert lines(build_chain(), mars) == ['300', '20', '1', '99', '333', '22', '99', '11']


def test_env_01_links_come_from_each_ancestor_layout():
    _, plan, _ = assemble(build_chain())
    assert plan.environment_access('D', 0, 0).links == ()
    assert plan.environment_access('D', 1, 4).links == (8,)        # C keeps its link at 8
    assert plan.environment_access('D', 2, 0).links == (8, 16)     # then B, at 16
    assert plan.environment_access('D', 2, 0).target == 'A'
    with pytest.raises(MipsError, match='MISSING-LAYOUT'):         # there is no fourth ancestor
        plan.environment_access('D', 3, 0)
    with pytest.raises(MipsError, match='INVALID-ADDRESS'):        # outside the environment of A
        plan.environment_access('D', 2, 16)
    with pytest.raises(MipsError, match='MISSING-LAYOUT'):         # A receives no environment
        plan.environment_access('A', 0, 0)


def test_env_01_rejects_unresolvable_access():
    m = Model()
    lone = m.procedure('lone', hidden=('env',))  # no lexical parent is known
    get(lone, lone.param('env'), (0, 0))
    lone.ret()
    m.global_.call('lone', [NULL_CONSTANT])
    reject(m, 'MIPS-MISSING-LAYOUT')

    m = Model()
    p = m.procedure('p')
    new_env(p, 16, FLOAT)
    p.ret()
    m.global_.call('p')
    reject(m, 'MIPS-TYPE')  # an environment pointer cannot live in a double register

    m = Model()
    p = m.procedure('p')
    put(p, new_env(p, 16), 4, const(1.5, FLOAT))  # a double cell must be eight-byte aligned
    p.ret()
    m.global_.call('p')
    reject(m, 'MIPS-INVALID-ADDRESS')

    m = Model()
    p = m.procedure('p')
    new_env(p, 0)
    p.ret()
    m.global_.call('p')
    reject(m, 'MIPS-INVALID-ADDRESS')


def test_env_01_double_boolean_and_reference_cells(mars):
    m = Model()
    p = m.procedure('p')
    env = new_env(p, 32, BOX)
    put(p, env, 0, const(2.5, FLOAT))
    put(p, env, 8, const(True, BOOLEAN))
    put(p, env, 12, const(-9))
    put(p, env, 16, env)  # a reference to itself
    p.show(get(p, env, 0, FLOAT))
    p.show(get(p, env, 8, BOOLEAN))
    p.show(get(p, env, 12))
    p.show(p.binary(O.EQ, get(p, env, 16, BOX), env, BOOLEAN))
    p.ret()
    m.global_.call('p')
    assert lines(m, mars) == ['2.5', 'true', '-9', 'true']


# ---------------------------------------------------------------- ENV-02 escaping closures

def build_counter_model():
    m = Model()
    env = Model.environment('make', [('count', INTEGER, 0)], 8, 16)
    make = m.procedure('make', environment=env)
    inc = m.procedure('inc', hidden=('env',), parent='make')
    clobber = m.procedure('clobber')
    cells = [clobber.local(f'v{i}', INTEGER) for i in range(40)]
    for cell in cells:
        clobber.copy(const(0x7777), cell)
    clobber.ret()
    cell = new_env(make, 16)
    put(make, cell, 0, const(0))
    make.ret(closure(make, 'inc', cell, COUNTER))
    value = get(inc, inc.param('env'), (0, 0))
    bumped = inc.binary(O.ADD, value, const(1))
    put(inc, inc.param('env'), (0, 0), bumped)
    inc.ret(bumped)
    return m


def test_env_02_escape(mars):
    m = build_counter_model()
    g = m.global_
    first = m.static('first', COUNTER)
    second = m.static('second', COUNTER)
    g.copy(g.call('make', [], COUNTER, keep=True), first)
    g.show(g.call_indirect(first, [], INTEGER))
    g.show(g.call_indirect(first, [], INTEGER))
    g.call('clobber')                                  # reuses the stack make() once occupied
    g.show(g.call_indirect(first, [], INTEGER))
    g.copy(g.call('make', [], COUNTER, keep=True), second)
    g.show(g.call_indirect(second, [], INTEGER))      # a new creator starts again at one
    g.show(g.call_indirect(first, [], INTEGER))       # ...without disturbing the old one
    assert lines(m, mars) == ['1', '2', '3', '1', '4']


def test_env_02_escape_through_two_levels(mars):
    """The leaf reads its parent's cell by access link, long after both frames ended."""
    m = Model()
    outer_env = Model.environment('make2', [('x', INTEGER, 0)], 8, 16)
    mid_env = Model.environment('mid', [('y', INTEGER, 0)], 8, 16)
    make2 = m.procedure('make2', environment=outer_env)
    mid = m.procedure('mid', hidden=('env',), parent='make2', environment=mid_env)
    leaf = m.procedure('leaf', hidden=('env',), parent='mid')
    wipe = m.procedure('wipe')
    for number in range(30):
        wipe.copy(const(-1), wipe.local(f'w{number}', INTEGER))
    wipe.ret()
    ex = new_env(make2, 16)
    put(make2, ex, 0, const(10))
    make2.ret(make2.call_indirect(closure(make2, 'mid', ex, FunctionType((), COUNTER)), [], COUNTER))
    ey = new_env(mid, 16)
    put(mid, ey, 8, mid.param('env'))
    put(mid, ey, 0, const(5))
    mid.ret(closure(mid, 'leaf', ey, COUNTER))
    leaf.ret(leaf.binary(O.ADD, get(leaf, leaf.param('env'), (1, 0)),
                         leaf.binary(O.MUL, get(leaf, leaf.param('env'), (0, 0)), const(100))))
    g = m.global_
    held = m.static('held', COUNTER)
    g.copy(g.call('make2', [], COUNTER, keep=True), held)
    g.call('wipe')
    g.show(g.call_indirect(held, [], INTEGER))
    assert lines(m, mars) == ['510']


def test_env_02_null_and_corrupt_callables_report_errors(mars):
    m = Model()
    never = m.static('never', COUNTER)
    m.global_.call_indirect(never, [], INTEGER)
    result, _, _, _ = execute(m, mars)
    assert (result.status, result.returncode) == ('runtime_error', 1)
    assert result.stdout == 'RuntimeError: NULL_ACCESS\n'

    m = build_counter_model()
    g = m.global_
    held = m.static('held', COUNTER)
    g.copy(g.call('make', [], COUNTER, keep=True), held)
    g.emit(O.ENV_SET, held, offset(24), const(7))        # no such hidden-parameter mask
    g.call_indirect(held, [], INTEGER)
    result, _, _, _ = execute(m, mars)
    assert (result.status, result.returncode) == ('runtime_error', 1)
    assert result.stdout == 'RuntimeError: INVALID_CALLABLE\n'


def test_env_02_rejects_inconsistent_closures():
    m = build_counter_model()
    g = m.global_
    g.emit(O.CLOSURE, label('inc'), NULL_CONSTANT, g.tmp(COUNTER))      # inc needs its environment
    reject(m, 'MIPS-INVALID-IR')

    m = build_counter_model()
    g = m.global_
    env = new_env(g, 16)
    g.emit(O.CLOSURE, label('clobber'), env, g.tmp(THUNK))             # clobber takes none
    reject(m, 'MIPS-INVALID-IR')

    m = build_counter_model()
    g = m.global_
    g.emit(O.CLOSURE, label('missing'), NULL_CONSTANT, g.tmp(THUNK))
    reject(m, 'MIPS-UNKNOWN-EXTERNAL')

    m = build_counter_model()
    g = m.global_
    held = m.static('held', COUNTER)
    g.emit(O.PARAM, const(1))
    g.emit(O.CLOSURE_CALL, held, const(1), g.tmp(INTEGER))             # signature takes no argument
    reject(m, 'MIPS-CALL-ARITY')

    m = build_counter_model()
    g = m.global_
    held = m.static('held', COUNTER)
    g.emit(O.CLOSURE_CALL, held, const(0), g.tmp(FLOAT))               # integer function, double result
    reject(m, 'MIPS-CALL-SIGNATURE')


# ---------------------------------------------------------------- ENV-03 shared captures

def build_shared_model():
    m = Model()
    env = Model.environment('outer', [('count', INTEGER, 0)], 8, 16)
    outer = m.procedure('outer', environment=env)
    inc = m.procedure('inc', hidden=('env',), parent='outer')
    dec = m.procedure('dec', hidden=('env',), parent='outer')
    relay = m.procedure('relay', hidden=('env',), parent='outer')
    for step, op in ((inc, O.ADD), (dec, O.SUB)):
        put(step, step.param('env'), (0, 0),
            step.binary(op, get(step, step.param('env'), (0, 0)), const(1)))
        step.ret()
    # relay only forwards: it never touches the counter, yet it needs the environment.
    relay.call_indirect(closure(relay, 'inc', relay.param('env'), THUNK))
    relay.ret()
    cell = new_env(outer, 16)
    put(outer, cell, 0, const(0))
    ci, cd, cr = closure(outer, 'inc', cell, THUNK), closure(outer, 'dec', cell, THUNK), \
        closure(outer, 'relay', cell, THUNK)
    outer.call_indirect(ci)
    outer.call_indirect(ci)
    outer.call_indirect(cd)
    outer.show(get(outer, cell, 0))
    outer.call_indirect(cr)
    outer.show(get(outer, cell, 0))
    outer.ret()
    return m


def test_env_03_shared_capture(mars):
    m = build_shared_model()
    m.global_.call('outer')
    m.global_.call('outer')
    # inc, inc, dec -> 1; the relay (which only calls inc) -> 2; a second creator restarts at 0.
    assert lines(m, mars) == ['1', '2', '1', '2']


# ---------------------------------------------------------------- METHOD-01 bound methods

def build_method_model():
    m = Model()
    m.receiver_type = BOX
    env = Model.environment('maker', [('captured', INTEGER, 0)], 8, 16)
    maker = m.procedure('maker', environment=env)
    plain = m.procedure('plain', [('k', INTEGER)])
    scaled = m.procedure('scaled', [('k', INTEGER)], hidden=('env',), parent='maker')
    getter = m.procedure('getter', [('k', INTEGER)], hidden=('this',))
    bound = m.procedure('bound', [('k', INTEGER)], hidden=('this', 'env'), parent='maker',
                        bound_environment_offset=8)
    plain.ret(plain.binary(O.ADD, plain.param('k'), const(100)))
    scaled.ret(scaled.binary(O.ADD, scaled.param('k'), get(scaled, scaled.param('env'), (0, 0))))
    getter.ret(getter.binary(O.ADD, getter.param('k'), get(getter, getter.param('this'), 0)))
    # Asymmetric on purpose: swapping `this` and `env` must change the result.
    inner = bound.binary(O.ADD, bound.binary(O.MUL, get(bound, bound.param('this'), 0), const(3)),
                         get(bound, bound.param('env'), (0, 0)))
    bound.ret(bound.binary(O.ADD, bound.param('k'), inner))
    cell = new_env(maker, 16)
    put(maker, cell, 0, const(1000))
    receiver = new_env(maker, 16, BOX)
    put(maker, receiver, 0, const(7))        # field
    put(maker, receiver, 8, cell)            # environment captured at construction
    maker.ret(receiver)
    return m


def test_method_01_bound_call(mars):
    m = build_method_model()
    g = m.global_
    variable = m.static('variable', UNARY)
    receiver_slot = m.static('receiver', BOX)
    g.copy(g.call('maker', [], BOX, keep=True), receiver_slot)   # the creator is gone from now on

    def run(_title):
        g.show(g.call_indirect(variable, [const(5)], INTEGER))

    g.copy(closure(g, 'plain', NULL_CONSTANT, UNARY), variable)            # mask 0
    run('global function')
    environment = get(g, receiver_slot, 8, UNKNOWN)
    g.copy(closure(g, 'scaled', environment, UNARY), variable)             # mask 1
    run('closure with environment')
    g.copy(g.emit(O.METHOD_REF, receiver_slot, label('getter'), g.tmp(UNARY)), variable)   # mask 2
    run('method')
    live = g.emit(O.METHOD_REF, receiver_slot, label('bound'), g.tmp(UNARY))                # mask 3
    g.copy(live, variable)
    run('method with environment')
    g.emit(O.ENV_SET, receiver_slot, offset(0), const(9))                  # the receiver is shared
    g.show(g.call_indirect(live, [const(5)], INTEGER))
    # 5+100, 5+1000, 5+7, 5+3*7+1000, then the same descriptor sees the new field: 5+3*9+1000
    assert lines(m, mars) == ['105', '1005', '12', '1026', '1032']


def test_method_01_rejects_invalid_callables(mars):
    m = build_method_model()
    g = m.global_
    g.emit(O.METHOD_REF, NULL_CONSTANT, label('getter'), g.tmp(UNARY))
    reject(m, 'MIPS-TYPE')

    m = build_method_model()
    g = m.global_
    receiver = m.static('receiver', BOX)
    g.emit(O.METHOD_REF, receiver, label('plain'), g.tmp(UNARY))          # not a method
    reject(m, 'MIPS-INVALID-IR')

    m = build_method_model()
    g = m.global_
    g.emit(O.CLOSURE, label('getter'), NULL_CONSTANT, g.tmp(UNARY))       # a method needs its receiver
    reject(m, 'MIPS-INVALID-IR')

    m = build_method_model()  # null receiver is a controlled language error, not a crash
    g = m.global_
    empty = m.static('empty', BOX)
    g.emit(O.METHOD_REF, empty, label('getter'), g.tmp(UNARY))
    result, _, _, _ = execute(m, mars)
    assert (result.status, result.returncode) == ('runtime_error', 1)
    assert result.stdout == 'RuntimeError: NULL_ACCESS\n'


# ---------------------------------------------------------------- hidden parameters, not duplicated

def test_indirect_calls_with_doubles_booleans_and_both_hidden_kinds(mars):
    """Hidden words come first at run time; explicit mixed arguments keep their positions."""
    m = Model()
    m.receiver_type = BOX
    env = Model.environment('maker', [('bonus', FLOAT, 0)], 8, 16)
    maker = m.procedure('maker', environment=env)
    shape = FunctionType((INTEGER, FLOAT, BOOLEAN), FLOAT)
    with_env = m.procedure('with_env', [('i', INTEGER), ('d', FLOAT), ('b', BOOLEAN)],
                           hidden=('env',), parent='maker')
    method = m.procedure('method', [('i', INTEGER), ('d', FLOAT), ('b', BOOLEAN)],
                         hidden=('this', 'env'), parent='maker', bound_environment_offset=8)
    skip = label('skip')
    for proc, receiver in ((with_env, None), (method, 'this')):
        proc.emit(O.IF_TRUE, proc.param('b'), None, skip)
        proc.ret(const(-1.0, FLOAT))
        proc.emit(O.LABEL, None, None, skip)
        scaled = proc.binary(O.MUL, proc.param('d'), proc.binary(O.ADD, const(0.0, FLOAT), const(2.0, FLOAT), FLOAT), FLOAT)
        total = proc.binary(O.ADD, scaled, get(proc, proc.param('env'), (0, 0), FLOAT), FLOAT)
        if receiver:
            total = proc.binary(O.SUB, total, get(proc, proc.param('this'), 0, FLOAT), FLOAT)
        proc.ret(proc.binary(O.ADD, total, proc.emit(O.CAST, proc.param('i'), label('float'), proc.tmp(FLOAT)),
                             FLOAT))
        skip = label('skip2')
    cell = new_env(maker, 16)
    put(maker, cell, 0, const(0.25, FLOAT))
    holder = new_env(maker, 24, BOX)
    put(maker, holder, 0, const(1.5, FLOAT))
    put(maker, holder, 8, cell)
    maker.ret(holder)
    g = m.global_
    receiver = m.static('receiver', BOX)
    callee = m.static('callee', shape)
    g.copy(g.call('maker', [], BOX, keep=True), receiver)
    environment = get(g, receiver, 8, UNKNOWN)
    g.copy(closure(g, 'with_env', environment, shape), callee)                      # mask 1
    g.show(g.call_indirect(callee, [const(3), const(2.0, FLOAT), const(True, BOOLEAN)], FLOAT))
    g.show(g.call_indirect(callee, [const(3), const(2.0, FLOAT), const(False, BOOLEAN)], FLOAT))
    g.copy(g.emit(O.METHOD_REF, receiver, label('method'), g.tmp(shape)), callee)  # mask 3
    g.show(g.call_indirect(callee, [const(3), const(2.0, FLOAT), const(True, BOOLEAN)], FLOAT))
    # 2.0*2 + 0.25 + 3 ; the failing branch ; the same minus the receiver's 1.5
    assert lines(m, mars) == ['7.25', '-1.0', '5.75']


def test_direct_calls_carry_their_hidden_parameters_explicitly(mars):
    """CALL counts the hidden PARAMs of the TAC; the backend must not add them again."""
    m = build_method_model()
    g = m.global_
    receiver = m.static('receiver', BOX)
    g.copy(g.call('maker', [], BOX, keep=True), receiver)
    environment = get(g, receiver, 8, UNKNOWN)
    g.show(g.call('bound', [receiver, environment, const(5)], INTEGER, keep=True))   # this, env, k
    g.show(g.call('getter', [receiver, const(5)], INTEGER, keep=True))     # this, k
    g.show(g.call('scaled', [environment, const(5)], INTEGER))            # env, k
    assert lines(m, mars) == ['1026', '12', '1005']
    m = build_method_model()
    m.global_.call('bound', [m.static('receiver', BOX), const(5)], INTEGER)   # env missing
    reject(m, 'MIPS-INVALID-IR')

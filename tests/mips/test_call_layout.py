"""ABI-01: physical frames, static data and checked rejection of broken layouts."""
import pytest

from abi_harness import LOCATION, NULL_CONSTANT, Model, assemble, const, label, lines
from src.codegen.activation import RuntimeLayouts
from src.codegen.ir import IRProgram, OpCode as O
from src.codegen.layout import ClassLayout
from src.mips.diagnostics import MipsError
from src.mips.layout import (
    HEADER_SIZE, PhysicalFrame, PhysicalLayoutPlan, _temporary_intervals, signature_of,
)
from src.mips.models import MachineLocation
from src.semantic.symbol_table import Symbol, SymbolKind
from src.semantic.types import BOOLEAN, FLOAT, INTEGER, ClassType


def build_two_functions():
    m = Model()
    f = m.procedure('f', [('p', INTEGER), ('q', FLOAT), ('ok', BOOLEAN)])
    outer = f.local('x', INTEGER)
    inner = f.local('x', INTEGER)  # shadows the first one
    wide = f.local('w', FLOAT)
    flag = f.local('flag', BOOLEAN)
    f.copy(const(1), outer)
    f.copy(const(2), inner)
    f.copy(const(2.5, FLOAT), wide)
    f.copy(const(True, BOOLEAN), flag)
    f.show(f.param('p'))
    f.show(f.param('q'))
    f.show(f.param('ok'))
    f.show(wide)
    f.show(flag)
    f.ret(f.binary(O.ADD, f.binary(O.MUL, outer, const(10)), inner))
    g = m.procedure('g', [('p', INTEGER)])
    mine = g.local('x', INTEGER)
    g.copy(const(7), mine)
    g.ret(g.binary(O.ADD, mine, g.param('p')))
    m.global_.show(m.global_.call('f', [const(3), const(0.5, FLOAT), const(False, BOOLEAN)], INTEGER))
    m.global_.show(m.global_.call('g', [const(5)], INTEGER))
    return m, f, g


def test_abi_01_frame_mapping(mars):
    m, f, g = build_two_functions()
    assembly, plan, _ = assemble(m)
    frame = plan.frame('f')
    symbols = {id(op.value.symbol): op for op in (f.param('p'), f.param('q'), f.param('ok'))}
    locals_ = [plan.address_of(op.value.symbol, 'f') for _, op in f._locals]
    # Shadowed declarations own different cells, none of them inside the header.
    assert locals_[0].offset != locals_[1].offset
    assert all(location.offset >= HEADER_SIZE for location in locals_)
    # Alignment: every access starts at a multiple of its width; the frame at eight.
    every = [*locals_, *[plan.address_of(op.value.symbol, 'f') for op in symbols.values()],
             *frame.temporaries.values()]
    assert all(location.offset % location.width == 0 for location in every)
    assert frame.size % 8 == 0
    # Complete slots: parameters sit in the incoming area, in declaration order.
    for index, name in enumerate(('p', 'q', 'ok')):
        location = plan.address_of(f.param(name).value.symbol, 'f')
        assert location.offset == frame.size + 8 * index and location.base == '$fp'
    assert plan.address_of(f.param('q').value.symbol, 'f').width == 8
    assert plan.address_of(f.param('ok').value.symbol, 'f').width == 4  # normalized word in ABI slots
    other = plan.address_of(g._locals[0][0], 'g')
    assert other.offset >= HEADER_SIZE and plan.frame('g').size % 8 == 0
    # Executed: each function reads its own storage back unchanged.
    assert lines(m, mars) == ['3', '0.5', 'false', '2.5', 'true', '12', '12']


def test_abi_01_rejects_broken_frames():
    cell = MachineLocation('$fp', 32, 8, 4)
    with pytest.raises(MipsError, match='INVALID-ADDRESS'):  # too small for its own slot
        PhysicalFrame('f', 32, 0, {}, {1: cell}, {})
    with pytest.raises(MipsError, match='INVALID-ADDRESS'):  # not a multiple of eight
        PhysicalFrame('f', 44, 0, {}, {1: cell}, {})
    with pytest.raises(MipsError, match='overlapping'):  # two locals on one cell
        PhysicalFrame('f', 48, 0, {}, {1: cell, 2: MachineLocation('$fp', 36, 4, 4)}, {})
    with pytest.raises(MipsError, match='INVALID-ADDRESS'):  # slot inside the header
        PhysicalFrame('f', 48, 0, {}, {1: MachineLocation('$fp', 24, 8, 4)}, {})
    with pytest.raises(MipsError, match='INVALID-ADDRESS'):  # staging beyond the frame
        PhysicalFrame('f', 40, 0, {}, {}, {}, staging=2, staging_start=32)
    with pytest.raises(MipsError, match='INVALID-ADDRESS'):  # parameter outside the incoming area
        PhysicalFrame('f', 32, 1, {1: MachineLocation('$fp', 80, 8, 4)}, {}, {})
    with pytest.raises(MipsError, match='overlapping'):  # staging colliding with a local
        PhysicalFrame('f', 48, 0, {}, {1: cell}, {}, staging=1, staging_start=32)


def test_abi_01_rejects_foreign_symbols_leases_and_links():
    m, f, g = build_two_functions()
    _, plan, _ = assemble(m)
    foreign = g._locals[0][0]
    with pytest.raises(MipsError, match='INVALID-ADDRESS'):  # belongs to the frame of g
        plan.address_of(foreign, 'f')
    stranger = f.local('stranger', INTEGER).value.symbol
    with pytest.raises(LookupError):
        plan.address_of(stranger, 'f')
    with pytest.raises(LookupError):
        plan.address_of(foreign, 'nowhere')
    lease = next(iter(plan.frame('f').temporaries))
    with pytest.raises(MipsError, match='INVALID-ADDRESS'):
        plan.temporary_slot(lease, 'g')
    with pytest.raises(LookupError):
        plan.temporary_slot((99, 99), 'f')
    with pytest.raises(MipsError, match='MISSING-LAYOUT'):  # no environment, no access link
        plan.environment_access('f', 0, 0)
    with pytest.raises(MipsError, match='INVALID-ADDRESS'):
        plan.environment_access('f', -1, 0)
    with pytest.raises(MipsError, match='INVALID-ADDRESS'):
        plan.environment_access('f', 0, -4)


def test_abi_01_object_offsets_are_preserved_and_checked():
    m = Model()
    box = Symbol('Box', SymbolKind.CLASS, ClassType('Box'), False, LOCATION)
    m.classes['Box'] = ClassLayout(box, 'Box', 24, 8, ())
    program, layouts, _ = m.build()
    plan = PhysicalLayoutPlan.build(program, layouts)
    for offset in (0, 4, 8, 16, 20):  # abstract offsets map to themselves (padding kept)
        assert plan.field_offset('Box', offset) == offset
        assert plan.field_offset(layouts.classes['Box'], offset) == offset
        assert plan.field_offset(ClassType('Box'), offset) == offset
    for bad in (-4, 24, 6, 4096, True, 2.0):
        with pytest.raises(MipsError, match='INVALID-ADDRESS'):
            plan.field_offset('Box', bad)
    with pytest.raises(LookupError):
        plan.field_offset('Missing', 0)


def test_abi_01_rejects_inconsistent_inputs():
    m, f, g = build_two_functions()
    program, layouts, parents = m.build()
    bare = RuntimeLayouts(layouts.symbols, {}, (), layouts.global_frame, None)
    with pytest.raises(MipsError, match='MISSING-LAYOUT'):  # frame absent from the layouts
        PhysicalLayoutPlan.build(program, bare)
    clone = IRProgram(program.global_code, (*program.procedures, program.procedures[0]))
    with pytest.raises(MipsError, match='INVALID-IR'):  # duplicate label
        PhysicalLayoutPlan.build(clone, layouts)

    m, f, g = build_two_functions()
    shared = f.tmp()
    f.emit(O.COPY, const(1), None, shared)
    g.emit(O.COPY, const(1), None, shared)  # the same lease in two procedures
    with pytest.raises(MipsError, match='INVALID-IR'):
        assemble(m)

    m, f, g = build_two_functions()
    program, layouts, parents = m.build()
    short = type(program.procedures[0])(program.procedures[0].label, program.procedures[0].parameters[:1],
                                       program.procedures[0].instructions)
    with pytest.raises(MipsError, match='MISSING-LAYOUT'):  # IR and layout disagree on arity
        PhysicalLayoutPlan.build(IRProgram(program.global_code, (short, *program.procedures[1:])), layouts)


def test_abi_01_hidden_parameters_lead_the_signature():
    m = Model()
    m.procedure('bad', [('a', INTEGER)], hidden=('env',))
    program, _, _ = m.build()
    assert signature_of(program.procedures[0]).hidden == ('env',) and signature_of(program.procedures[0]).mask == 1
    m = Model()
    m.procedure('both', [('a', INTEGER)], hidden=('this', 'env'), bound_environment_offset=8)
    program, _, _ = m.build()
    signature = signature_of(program.procedures[0])
    assert (signature.arity, signature.declared_arity, signature.mask) == (3, 1, 3)


def test_abi_01_temporary_cells_are_reused_only_after_release(mars):
    m = Model()
    g = m.global_
    # Disjoint lifetimes of three machine types share a cell; overlapping ones do not.
    integer = g.copy(const(7), g.tmp())
    g.show(integer)
    double = g.copy(const(2.5, FLOAT), g.tmp(FLOAT))
    g.show(double)
    truth = g.copy(const(True, BOOLEAN), g.tmp(BOOLEAN))
    g.show(truth)
    left, right = g.copy(const(1), g.tmp()), g.copy(const(2), g.tmp())
    g.show(g.binary(O.ADD, left, right))
    g.release(left, right)
    program, layouts, _ = m.build()
    plan = PhysicalLayoutPlan.build(program, layouts)
    frame = plan.frame('global')
    first = [frame.temporaries[t.lease].offset for t in (integer, double, truth)]
    assert len(set(first)) == 1  # one cell, three types, one after another
    assert frame.temporaries[left.lease].offset != frame.temporaries[right.lease].offset
    assert lines(m, mars) == ['7', '2.5', 'true', '3']


def test_abi_01_lease_alive_into_a_loop_keeps_its_cell():
    m = Model()
    g = m.global_
    keep = g.copy(const(5), g.tmp())
    top = label('top')
    g.emit(O.LABEL, None, None, top)
    g.copy(keep, g.tmp())
    g.release(keep)
    other = g.copy(const(1), g.tmp())
    g.emit(O.GOTO, None, None, top)
    spans = _temporary_intervals(g.instructions)
    assert spans[keep.lease][2] >= 5  # extended to the back edge
    assert spans[other.lease][1] > 0


def test_abi_01_statics_use_the_global_pointer(mars):
    m = Model()
    a, d, b = m.static('a', INTEGER), m.static('d', FLOAT), m.static('b', BOOLEAN)
    probe = m.procedure('probe')
    probe.copy(const(41), a)
    probe.copy(const(1.25, FLOAT), d)
    probe.copy(const(True, BOOLEAN), b)
    probe.ret()
    g = m.global_
    g.call('probe')
    g.show(g.binary(O.ADD, a, const(1)))
    g.show(d)
    g.show(b)
    program, layouts, _ = m.build()
    plan = PhysicalLayoutPlan.build(program, layouts)
    cells = [plan.address_of(op.value.symbol, 'probe') for op in (a, d, b)]
    assert all(cell.base == '$gp' and cell.offset % cell.width == 0 for cell in cells)
    assert plan.static_size % 8 == 0 and plan.static_size >= 16
    assert lines(m, mars) == ['42', '1.25', 'true']


def test_abi_01_incoming_formula_with_many_arguments(mars):
    """Argument i of n lives at fp + F + 8*i, for any mix of types, hidden ones first."""
    kinds = [INTEGER, FLOAT, BOOLEAN, INTEGER, FLOAT, INTEGER, BOOLEAN, FLOAT, INTEGER, INTEGER]
    m = Model()
    wide = m.procedure('wide', [(f'a{i}', kind) for i, kind in enumerate(kinds)], hidden=('env',))
    for i in (1, 4, 7):
        wide.show(wide.param(f'a{i}'))
    wide.show(wide.param('a9'))
    wide.ret()
    g = m.global_
    g.call('wide', [NULL_CONSTANT, *[const({INTEGER: i, FLOAT: i + 0.5, BOOLEAN: i % 2 == 0}[k], k)
                                        for i, k in enumerate(kinds)]])
    program, layouts, parents = m.build()
    plan = PhysicalLayoutPlan.build(program, layouts, parents=parents)
    frame = plan.frame('wide')
    assert frame.arity == 11
    for index, name in enumerate(['env', *[f'a{i}' for i in range(10)]]):
        location = plan.address_of(wide.param(name).value.symbol, 'wide')
        assert location.offset == frame.size + 8 * index
    assert lines(m, mars) == ['1.5', '4.5', '7.5', '9']


def test_abi_01_frame_size_is_bounded_by_the_offset_range():
    m = Model()
    big = m.procedure('big')
    for index in range(7000):
        big.local(f'v{index}', INTEGER)
    big.ret()
    m.global_.call('big')
    with pytest.raises(MipsError, match='16-bit'):
        assemble(m)


def test_abi_01_large_frames_are_cleared_and_never_leak_stale_values(mars):
    """Past 64 words the prologue zeroes the frame in a loop; locals start at zero."""
    m = Model()
    pairs = {}
    for prefix, count in (('big', 120), ('small', 6)):
        dirty, clean = m.procedure(f'{prefix}_dirty'), m.procedure(f'{prefix}_clean')
        written = [dirty.local(f'd{i}', INTEGER) for i in range(count)]
        for cell in written:
            dirty.copy(const(-1), cell)
        dirty.copy(const(-1), dirty.tmp())          # same shape as `clean`: one temporary
        dirty.ret()
        fresh = [clean.local(f'c{i}', INTEGER) for i in range(count)]
        clean.ret(clean.binary(O.ADD, fresh[0], fresh[-1]))
        pairs[prefix] = (dirty, clean, written, fresh)
    g = m.global_
    for prefix in ('big', 'small'):
        g.call(f'{prefix}_dirty')
        g.show(g.call(f'{prefix}_clean', [], INTEGER))   # same addresses `*_dirty` just filled with -1
    program, layouts, _ = m.build()
    plan = PhysicalLayoutPlan.build(program, layouts)
    for prefix, (dirty, clean, written, fresh) in pairs.items():
        # The premise of the test: both frames put every local at the very same address.
        assert plan.frame(f'{prefix}_dirty').size == plan.frame(f'{prefix}_clean').size
        assert [plan.address_of(o.value.symbol, f'{prefix}_dirty').offset for o in written] ==             [plan.address_of(o.value.symbol, f'{prefix}_clean').offset for o in fresh]
    assert plan.frame('big_clean').size // 4 > 64 + 4   # loop path
    assert plan.frame('small_clean').size // 4 < 64     # unrolled path
    assert lines(m, mars) == ['0', '0']


def test_abi_01_contracts_and_opcode_ownership():
    import inspect
    from src.codegen.ir import OpCode
    from src.mips.calls import CALL_OPCODES, CallingConvention, ProgramEmitter
    from src.mips.environments import ENV_OPCODES, EnvironmentHandler
    from src.mips.models import CallEmitter, InstructionHandler, LocationResolver
    from src.mips.scalar import SCALAR_OPCODES, ScalarLowerer

    def conforms(candidate, protocol):
        for name in (n for n in vars(protocol) if not n.startswith('_')):
            assert callable(getattr(candidate, name)), name
            assert list(inspect.signature(getattr(candidate, name)).parameters) == \
                list(inspect.signature(getattr(protocol, name)).parameters)[1:], name

    m, _, _ = build_two_functions()
    program, layouts, _ = m.build()
    plan = PhysicalLayoutPlan.build(program, layouts)
    conforms(plan, LocationResolver)
    calls, env = CallingConvention(plan), EnvironmentHandler(plan)
    conforms(calls, CallEmitter)
    for handler in (calls, env, ScalarLowerer()):
        conforms(handler, InstructionHandler)
    handlers = ProgramEmitter(plan).handlers
    for opcode in OpCode:
        owners = [h for h in handlers if h.supports(opcode)]
        assert len(owners) <= 1, opcode            # a single owner per opcode
        expected = opcode in CALL_OPCODES | ENV_OPCODES | SCALAR_OPCODES
        assert bool(owners) == expected, opcode    # lists, objects and exceptions wait for block 3
    assert CALL_OPCODES == {OpCode.PARAM, OpCode.CALL, OpCode.CLOSURE_CALL, OpCode.RETURN}
    assert ENV_OPCODES == {OpCode.ENV_NEW, OpCode.ENV_SET, OpCode.ENV_GET, OpCode.CLOSURE,
                           OpCode.METHOD_REF}


def test_abi_01_lease_released_in_both_branches_keeps_its_cell_until_the_last_release():
    """A RELEASE in one branch does not end the lifetime seen by the other branch."""
    m = Model()
    g = m.global_
    flag = m.static('flag', BOOLEAN)
    kept = g.copy(const(5), g.tmp())
    other, end = label('other'), label('end')
    g.emit(O.IF_FALSE, flag, None, other)
    g.release(kept)                               # first branch: done with it
    late = g.copy(const(9), g.tmp())              # would happily take a freed cell
    g.release(late)
    g.emit(O.GOTO, None, None, end)
    g.emit(O.LABEL, None, None, other)
    g.copy(kept, g.tmp())                         # second branch: still needs it
    g.release(kept)
    g.emit(O.LABEL, None, None, end)
    spans = _temporary_intervals(g.instructions)
    assert spans[kept.lease][2] == max(i for i, item in enumerate(g.instructions)
                                       if item.arg1 is not None and item.arg1.lease == kept.lease)
    program, layouts, _ = m.build()
    frame = PhysicalLayoutPlan.build(program, layouts).frame('global')
    assert frame.temporaries[kept.lease].offset != frame.temporaries[late.lease].offset


@pytest.mark.parametrize('taken,expected', [(True, ['5']), (False, ['9', '5'])])
def test_abi_01_lease_released_on_each_path_keeps_its_value_in_mars(mars, taken, expected):
    """In the other branch a new temporary must not overwrite the kept lease's cell."""
    m = Model()
    g = m.global_
    flag = m.static('flag', BOOLEAN)
    g.copy(const(taken, BOOLEAN), flag)
    kept = g.copy(const(5), g.tmp())
    other, end = label('other'), label('end')
    g.emit(O.IF_FALSE, flag, None, other)
    g.show(kept)
    g.emit(O.GOTO, None, None, end)
    g.emit(O.LABEL, None, None, other)
    g.show(g.copy(const(9), g.tmp()))
    g.show(kept)
    g.emit(O.LABEL, None, None, end)
    assert lines(m, mars) == expected

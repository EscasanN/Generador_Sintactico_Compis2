"""Block 2 against the real compiler: IR and runtime layouts come from Project 2.

Programs use only calls, closures, scalars and ``print`` so they do not wait for
the string, list, object or exception handlers of block 3.  The expected output
of every program is worked out by hand in the comment next to it.
"""
from pathlib import Path

import pytest

from src.codegen.ir import OpCode
from src.codegen.pipeline import compile_compiscript
from src.mips.calls import ProgramEmitter
from src.mips.diagnostics import MipsError
from src.mips.layout import HIDDEN_ORDER, PhysicalLayoutPlan
from src.mips.simulator import run_mars

FIXTURES = sorted(Path(__file__).resolve().parents[1].joinpath('cps', 'codegen', 'validos').glob('*.cps'))


def compile_program(source, path=None):
    result = compile_compiscript(source, path)
    assert result.accepted, result.failed_stage
    return result.intermediate_result


def run_source(source, mars, **options):
    ir = compile_program(source)
    plan = PhysicalLayoutPlan.build(ir.program, ir.layouts)
    assembly = ProgramEmitter(plan, **options).assemble(ir.program)
    result = run_mars(assembly, mars)
    assert result.accepted, (result.status, result.stdout, result.stderr[-300:])
    return result.stdout.splitlines()


NESTED = '''
function contador(inicio: integer): integer {
  let cuenta: integer = inicio;
  function incrementar(paso: integer): integer {
    cuenta = cuenta + paso;
    function doble(): integer { return cuenta * 2; }
    return doble();
  }
  incrementar(1);
  return incrementar(2);
}
print(contador(10));
function fact(n: integer): integer { if (n <= 1) { return 1; } return n * fact(n - 1); }
print(fact(5));
'''  # cuenta: 10 -> 11 -> 13, doble = 26; 5! = 120

ESCAPING = '''
function cero(): integer { return 0; }
let guardado = cero;
let otro = cero;
function instalar() {
  let n: integer = 0;
  function siguiente(): integer { n = n + 1; return n; }
  guardado = siguiente;
}
function instalar2() {
  let n: integer = 100;
  function siguiente2(): integer { n = n + 1; return n; }
  otro = siguiente2;
}
instalar();
instalar2();
print(guardado());
print(guardado());
print(otro());
print(guardado());
'''  # independent counters that outlive their creators: 1, 2, 101, 3

MIXED = '''
function media(a: float, b: float): float { return (a + b) / 2.0; }
print(media(1.0, 2.0));
function par(n: integer): boolean { if (n == 0) { return true; } return impar(n - 1); }
function impar(n: integer): boolean { if (n == 0) { return false; } return par(n - 1); }
print(par(10));
print(impar(10));
function varios(a: integer, b: float, c: boolean, d: integer, e: integer, f: integer): integer {
  if (c) { return a + d + e + f; }
  return 0;
}
print(varios(1, 2.5, true, 3, 4, 5));
let total: integer = 0;
function acumular(x: integer) { total = total + x; }
acumular(3);
acumular(4);
print(total);
'''  # 1.5, true, false, 1+3+4+5 = 13, 3+4 = 7

SIBLINGS = '''
function outer(): integer {
  let base: integer = 10;
  function incrementar(): integer { base = base + 1; return base; }
  function intermedia(): integer { return incrementar(); }
  function hermana(): integer {
    let guardada = intermedia;
    return guardada();
  }
  hermana();
  return hermana();
}
print(outer());
'''  # both siblings share one cell: 11 then 12


@pytest.mark.parametrize('source,expected', [
    (NESTED, ['26', '120']),
    (ESCAPING, ['1', '2', '101', '3']),
    (MIXED, ['1.5', 'true', 'false', '13', '7']),
    (SIBLINGS, ['12']),
], ids=['nested-and-recursion', 'escaping-closures', 'mixed-signatures', 'sibling-closures'])
def test_real_compiler_programs_run_in_mars(mars, source, expected):
    assert run_source(source, mars) == expected


def test_real_programs_survive_scarce_registers(mars):
    assert run_source(NESTED, mars, gpr_count=2, fpr_count=2) == ['26', '120']
    assert run_source(MIXED, mars, gpr_count=2, fpr_count=2) == ['1.5', 'true', 'false', '13', '7']


def test_lexical_parents_come_from_the_semantic_scopes():
    ir = compile_program(NESTED)
    plan = PhysicalLayoutPlan.build(ir.program, ir.layouts)
    assert dict(plan.parents) == {'fn_contador.incrementar': 'fn_contador',
                                  'fn_contador.incrementar.doble': 'fn_contador.incrementar'}
    # `doble` reaches `cuenta` (declared in `contador`) one access link away, through
    # the environment that `incrementar` built; the control link is never involved.
    access = plan.environment_access('fn_contador.incrementar.doble', 1, 0)
    assert access.target == 'fn_contador' and len(access.links) == 1


def test_opcodes_without_a_handler_are_rejected_not_ignored():
    ir = compile_program('let xs: integer[] = [1, 2, 3];\nprint(xs[0]);\n')
    plan = PhysicalLayoutPlan.build(ir.program, ir.layouts)
    with pytest.raises(MipsError) as caught:
        ProgramEmitter(plan).assemble(ir.program)
    assert caught.value.diagnostic.code == 'MIPS-UNSUPPORTED-OPCODE'


@pytest.mark.parametrize('path', FIXTURES, ids=[p.stem for p in FIXTURES])
def test_every_valid_project2_program_has_a_complete_physical_plan(path):
    result = compile_compiscript(path.read_text(encoding='utf-8'), path)
    assert result.accepted, path.name
    ir = result.intermediate_result
    plan = PhysicalLayoutPlan.build(ir.program, ir.layouts)
    assert set(plan.frames) == {'global', *(str(p.label.value) for p in ir.program.procedures)}
    for label, signature in plan.signatures.items():
        assert signature.hidden in HIDDEN_ORDER
        assert (signature.bound_environment_offset is not None) == (signature.hidden == ('this', 'env'))
        assert plan.frame(label).arity == signature.arity
    for procedure in ir.program.procedures:
        label = str(procedure.label.value)
        for item in procedure.instructions:
            if item.opcode in (OpCode.ENV_GET, OpCode.ENV_SET) and isinstance(item.arg2.value, tuple):
                depth, offset = item.arg2.value
                assert plan.environment_access(label, depth, offset).depth == depth

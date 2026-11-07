"""EXC-01..EXC-03: runtime errors, unwinding between frames and protected exits."""
import pytest

from abi_harness import CanaryProbe
from pipeline_harness import assemble_with_hooks, intermediate, output, run_source
from src.codegen.ir import OpCode
from src.mips.exceptions import HANDLER_RECORD_SIZE
from src.mips.generator import generate_mips
from src.mips.simulator import run_mars

CAUGHT = '''
class P { let v: integer; }
let ceroI: integer = 0;
let ceroF: float = 0.0;
let xs: integer[] = [1];
let nulo: P = null;
let i: integer = 1;
try { print(5 / ceroI); } catch (e) { print(e); }
try { print(5 % ceroI); } catch (e) { print(e); }
try { print(5.0 / ceroF); } catch (e) { print(e); }
try { print(5.0 % ceroF); } catch (e) { print(e); }
try { print(xs[i]); } catch (e) { print(e); }
try { print(nulo.v); } catch (e) { print(e); }
print("fin");
'''


def test_exc_01_errors(mars):
    assert output(CAUGHT, mars) == ['DIV_ZERO', 'DIV_ZERO', 'DIV_ZERO', 'DIV_ZERO',
                                    'INDEX_OUT_OF_RANGE', 'NULL_ACCESS', 'fin']


@pytest.mark.parametrize('statement,code', [
    ('print(1 / cero);', 'DIV_ZERO'),
    ('print(1 % cero);', 'DIV_ZERO'),
    ('print(1.0 / 0.0);', 'DIV_ZERO'),
    ('let xs: integer[] = [1]; print(xs[cero - 1]);', 'INDEX_OUT_OF_RANGE'),
    ('let s: string; print(s + "x");', 'NULL_ACCESS'),
])
def test_exc_01_without_handler_prints_code_and_exits_with_one(mars, statement, code):
    result = run_source(f'let cero: integer = 0;\nprint("antes");\n{statement}\nprint("nunca");\n',
                        mars, expect_success=False)
    # A controlled language error, not an arbitrary MARS trap: stdout ends with
    # the runtime message, MARS reports no exception and the exit code is 1.
    assert result.status == 'runtime_error' and result.returncode == 1
    assert result.stdout == f'antes\nRuntimeError: {code}\n'
    assert 'exception' not in result.stderr.lower()


UNWIND = '''
function dividir(a: integer, b: integer): integer { return a / b; }
function nivel(n: integer, b: integer): integer {
  let local: integer = n * 100;
  if (n == 0) { return dividir(local, b); }
  let parcial: integer = nivel(n - 1, b);
  return parcial + local;
}
let antes: integer = 7;
try {
  print(nivel(6, 0));
  print("nunca");
} catch (e) {
  print("capturado " + e);
}
print(antes);
print(nivel(3, 1));
try {
  try { print(nivel(2, 0)); } catch (e) { print("interno " + e); print(nivel(1, 0)); }
} catch (e2) { print("externo " + e2); }
let vueltas: integer = 0;
let k: integer = 0;
while (k < 100) {
  try { let r: integer = nivel(2, 0); } catch (e) { vueltas = vueltas + 1; }
  k = k + 1;
}
print(vueltas);
'''  # nivel(3,1) = 0 + 100 + 200 + 300 = 600; 100 catches without leaking stack


def test_exc_02_unwind(mars):
    expected = ['capturado DIV_ZERO', '7', '600', 'interno DIV_ZERO', 'externo DIV_ZERO', '100']
    assert output(UNWIND, mars) == expected
    assert output(UNWIND, mars, gpr_count=2, fpr_count=2) == expected


def test_exc_02_unwinding_restores_stack_frame_and_saved_registers(mars):
    probe = CanaryProbe()
    result = run_mars(assemble_with_hooks(UNWIND, probe.before, probe.after), mars)
    assert result.accepted, result.stderr[-300:]
    # The last line is the canary: $sp, $fp and $s0-$s7 equal their initial values.
    assert result.stdout.split('\n')[:-1][-1] == '1'


def test_exc_02_handler_head_is_restored_after_each_catch(mars):
    source = '''
let cero: integer = 0;
function protegida(): integer {
  try { return 1 / cero; } catch (e) { return -1; }
}
print(protegida());
try { print(2 / cero); } catch (e) { print("segundo"); }
print(3 / cero);
'''
    result = run_source(source, mars, expect_success=False)
    # Neither the function's nor the second handler survive: the last error is uncaught.
    assert result.returncode == 1
    assert result.stdout == '-1\nsegundo\nRuntimeError: DIV_ZERO\n'


TRANSFERS = '''
let cero: integer = 0;
function conReturn(b: boolean): integer {
  try { if (b) { return 1; } } catch (e) { return -1; }
  return 2;
}
print(conReturn(true) + conReturn(false));
try { print(1 / cero); } catch (e) { print("despues de return"); }
let k: integer = 0;
let pasos: integer = 0;
while (k < 6) {
  k = k + 1;
  try {
    try {
      if (k == 2) { continue; }
      if (k == 5) { break; }
      pasos = pasos + 1;
    } catch (e) { print("nunca"); }
  } catch (e) { print("nunca"); }
}
print(k * 10 + pasos);
try {
  foreach (x in [1, 2, 3]) {
    try { if (x == 2) { break; } } catch (e) { print("nunca"); }
  }
  print(1 / cero);
} catch (e) { print("exterior vigente"); }
function anidada(): integer {
  try { try { return 7; } catch (e) { return 8; } } catch (e) { return 9; }
}
print(anidada());
print(4 / cero);
'''  # 1+2 = 3; k = 5, pasos = 3 (k = 1, 3, 4): 53; after every exit no handler is left


def test_exc_03_transfers(mars):
    result = run_source(TRANSFERS, mars, expect_success=False)
    assert result.returncode == 1
    assert result.stdout.split('\n')[:-1] == [
        '3', 'despues de return', '53', 'exterior vigente', '7', 'RuntimeError: DIV_ZERO']


PRESSURE_IN_CATCH = '''
let cero: integer = 0;
let a: integer = 1;
let b: integer = 2;
let c: integer = 3;
let d: float = 0.5;
try {
  let t: integer = a + b + c;
  print(t / cero);
} catch (e) {
  let x: integer = a * 10 + b;
  let y: integer = c * 100 + x;
  let z: float = d + d + d;
  print(e + "!");
  print(x + y + a + b + c);
  print(z);
}
'''  # x = 12, y = 312: 12 + 312 + 6 = 330; z = 1.5


@pytest.mark.parametrize('banks', [(8, 5), (2, 2)], ids=['full-bank', 'two-registers'])
def test_exc_03_register_pressure_inside_catch(mars, banks):
    assert output(PRESSURE_IN_CATCH, mars, gpr_count=banks[0], fpr_count=banks[1]) == [
        'DIV_ZERO!', '330', '1.5']


def test_exc_03_records_are_pushed_and_retired_symmetrically():
    ir = intermediate(TRANSFERS)
    generated = generate_mips(ir)
    assert generated.accepted, generated.diagnostics
    units = (ir.program.global_code, *(p.instructions for p in ir.program.procedures))
    begins = sum(1 for unit in units for i in unit if i.opcode is OpCode.TRY_BEGIN)
    ends = sum(1 for unit in units for i in unit if i.opcode is OpCode.TRY_END)
    text = generated.assembly
    assert text.count(f'addiu $sp, $sp, -{HANDLER_RECORD_SIZE}') == begins
    # one retirement per TRY_END the TAC emitted (return/break/continue included), none extra
    assert text.count(f'addiu $sp, $sp, {HANDLER_RECORD_SIZE}') == ends

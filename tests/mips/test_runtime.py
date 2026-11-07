"""STR-01: strings, print and the runtime helpers (block 3).

Programs come from the real compiler; outputs are worked out by hand.
"""
import pytest

from abi_harness import CanaryProbe
from pipeline_harness import assemble_with_hooks, intermediate, mutate, output, run_source
from src.codegen.ir import OpCode, Operand, OperandKind
from src.mips.generator import generate_mips
from src.mips.simulator import run_mars
from src.semantic.types import STRING, UNKNOWN

STRINGS = '''
let a: string = "Compi";
let b: string = "script";
let c: string = a + b;
print(c);
let d: string = "Comp" + "iscript";
print(c == d);
print(c != d);
print("abc" < "abd");
print("abd" < "abc");
print("abc" < "ab");
print("ab" < "abc");
print("ab" <= "ab");
print("b" > "a");
print("a" >= "b");
print("Z" < "a");
print("é" > "z");
let vacia: string = "";
print(vacia == "");
print(vacia + "x" + vacia);
print(vacia);
print("canción ñandú €");
'''  # Compiscript; equal contents at distinct addresses; byte order (Z=90 < a=97, é=0xC3 > z)

NULLS = '''
let sinValor: string;
let vacia: string = "";
print(sinValor);
print(sinValor == vacia);
print(vacia == sinValor);
print(sinValor == sinValor);
print(sinValor != "x");
'''  # null prints null, is not "", equals only itself


def test_str_01_strings(mars):
    assert output(STRINGS, mars) == [
        'Compiscript', 'true', 'false', 'true', 'false', 'false', 'true', 'true', 'true',
        'false', 'true', 'true', 'true', 'x', '', 'canción ñandú €']


def test_str_01_null_is_not_the_empty_string(mars):
    assert output(NULLS, mars) == ['null', 'false', 'false', 'true', 'true']


@pytest.mark.parametrize('expression', ['sinValor + "x"', '"x" + sinValor', 'sinValor < "x"'])
def test_str_01_null_strings_are_never_dereferenced(mars, expression):
    source = f'let sinValor: string;\nprint("antes");\nprint({expression});\nprint("nunca");\n'
    result = run_source(source, mars, expect_success=False)
    assert result.status == 'runtime_error' and result.returncode == 1
    assert result.stdout == 'antes\nRuntimeError: NULL_ACCESS\n'


def test_str_01_literals_are_numeric_utf8_bytes_with_explicit_length():
    generated = generate_mips(intermediate('print("ñ€");\nprint("ñ€");\n'))
    assert generated.accepted, generated.diagnostics
    # length 5 (2 + 3 UTF-8 bytes), one shared object, no assembler escapes
    assert generated.assembly.count('.word 5, 0') == 1
    assert '.byte 195, 177, 226, 130, 172' in generated.assembly
    assert '.asciiz' not in generated.assembly


PRESSURE = '''
function mezclar(a: integer, s: string, b: integer): string {
  let x: integer = a * 2;
  let y: integer = b + 3;
  let t: string = s + "-" + s;
  let z: integer = x + y;
  if (t == "ab-ab" && z > 10) { return t + "!"; }
  return t;
}
let n1: integer = 1;
let n2: integer = 2;
let n3: integer = 3;
let suma: integer = n1 + n2;
let r: string = mezclar(suma, "ab", n3 * 4);
let otra: string = r + "?";
print(n1 + n2 + n3 + suma);
print(otra);
let lista: string[] = ["x", "y", "z"];
let acc: string = "";
foreach (e in lista) { acc = acc + e; }
print(acc < "xz");
print(acc);
'''  # x=6, y=15, z=21: "ab-ab!?"; live integers around helpers: 1+2+3+3 = 9


@pytest.mark.parametrize('banks', [(8, 5), (2, 2)], ids=['full-bank', 'two-registers'])
def test_str_01_helpers_do_not_clobber_live_values(mars, banks):
    assert output(PRESSURE, mars, gpr_count=banks[0], fpr_count=banks[1]) == [
        '9', 'ab-ab!?', 'true', 'xyz']


def test_str_01_helpers_preserve_stack_and_saved_registers(mars):
    probe = CanaryProbe()
    assembly = assemble_with_hooks(PRESSURE, probe.before, probe.after)
    result = run_mars(assembly, mars)
    assert result.accepted, result.stderr[-300:]
    assert result.stdout.split('\n')[:-1] == ['9', 'ab-ab!?', 'true', 'xyz', '1']


MARKERS = '''
class Caja { let v: integer = 1; }
function f(): integer { return 1; }
let xs: integer[] = [1];
let caja: Caja = new Caja();
let g = f;
let nadaLista: integer[] = null;
let nadaCaja: Caja = null;
print(xs);
print(caja);
print(g);
print(nadaLista);
print(nadaCaja);
print(1.5);
print(true);
print(-3);
'''


def test_str_01_print_dispatches_by_type_with_stable_markers(mars):
    assert output(MARKERS, mars) == ['[list]', '[object]', '[function]', 'null', 'null',
                                     '1.5', 'true', '-3']


def test_str_01_operations_undefined_for_strings_are_rejected_with_location():
    ir = intermediate('let a: string = "x";\nlet b: string = a + "y";\n')
    broken = mutate(ir, lambda i: i.opcode is OpCode.ADD and i.result.type == STRING,
                    lambda i: type(i)(OpCode.SUB, i.arg1, i.arg2, i.result, i.source_location))
    generated = generate_mips(broken)
    assert not generated.accepted and generated.assembly == ''
    (diagnostic,) = generated.diagnostics
    assert diagnostic.code == 'MIPS-TYPE' and diagnostic.location is not None


def test_str_01_print_of_an_unresolved_type_is_rejected():
    ir = intermediate('print(1);\n')
    broken = mutate(ir, lambda i: i.opcode is OpCode.PARAM,
                    lambda i: type(i)(OpCode.PARAM, Operand(OperandKind.CONSTANT, 1, UNKNOWN),
                                      None, None, i.source_location))
    generated = generate_mips(broken)
    assert [d.code for d in generated.diagnostics] == ['MIPS-UNRESOLVED-TYPE']
    assert generated.diagnostics[0].location is not None

"""LIST-01: lists with header, stride 8, typed elements and checked accesses."""
import pytest

from pipeline_harness import intermediate, mutate, output, run_source
from src.codegen.ir import OpCode, Operand, OperandKind
from src.mips.generator import generate_mips
from src.semantic.types import FLOAT, INTEGER

OPERATIONS = '''
let xs: integer[] = [1, 2, 3];
let suma: integer = 0;
foreach (x in xs) { suma = suma + x; }
print(suma);
let vacia = [];
let vueltas: integer = 0;
foreach (v in vacia) { vueltas = vueltas + 1; }
print(vueltas);
let dobles: float[] = [0.5, 1.25, 2.0];
let total: float = 0.0;
foreach (d in dobles) { total = total + d; }
print(total);
let banderas: boolean[] = [false, true, false];
print(banderas[1]);
print(banderas[2]);
let matriz: integer[][] = [[1, 2, 3], [4, 5, 6]];
let diagonal: integer = matriz[0][0] + matriz[1][1];
matriz[1][2] = diagonal;
print(matriz[1][2]);
let fila: integer[] = matriz[1];
fila[0] = 40;
print(matriz[1][0]);
let palabras: string[] = ["a", "b"];
palabras[0] = palabras[1] + palabras[0];
print(palabras[0]);
class Celda { let v: integer = 7; }
let celdas: Celda[] = [new Celda(), new Celda()];
celdas[1].v = 8;
print(celdas[0].v + celdas[1].v);
let grande: integer[] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
let i: integer = 0;
while (i < 20) { grande[i] = i * i; i = i + 1; }
print(grande[19] + grande[3]);
'''  # 6; 0; 3.75; true; false; 1+5 = 6; alias sees 40; "ba"; 7+8 = 15; 361+9 = 370


@pytest.mark.parametrize('banks', [(8, 5), (2, 2)], ids=['full-bank', 'two-registers'])
def test_list_01_operations(mars, banks):
    assert output(OPERATIONS, mars, gpr_count=banks[0], fpr_count=banks[1]) == [
        '6', '0', '3.75', 'true', 'false', '6', '40', 'ba', '15', '370']


@pytest.mark.parametrize('index,code', [('-1', 'INDEX_OUT_OF_RANGE'), ('3', 'INDEX_OUT_OF_RANGE'),
                                        ('2', None)])
def test_list_01_bounds_are_checked_before_reading(mars, index, code):
    source = f'let xs: integer[] = [10, 20, 30];\nlet i: integer = {index};\nprint(xs[i]);\n'
    result = run_source(source, mars, expect_success=code is None)
    if code is None:
        assert result.stdout == '30\n'
    else:
        assert result.status == 'runtime_error' and result.returncode == 1
        assert result.stdout == f'RuntimeError: {code}\n'


@pytest.mark.parametrize('statement', ['xs[i] = 5;', 'print(xs[i]);', 'foreach (x in xs) { print(x); }'],
                         ids=['store', 'load', 'foreach-length'])
def test_list_01_null_lists_raise_null_access(mars, statement):
    source = f'let xs: integer[] = null;\nlet i: integer = 0;\n{statement}\n'
    result = run_source(source, mars, expect_success=False)
    assert result.returncode == 1 and result.stdout == 'RuntimeError: NULL_ACCESS\n'


def test_list_01_store_out_of_range_never_writes_a_neighbour(mars):
    source = '''
let a: integer[] = [1, 2];
let b: integer[] = [3, 4];
let i: integer = 2;
try { a[i] = 99; } catch (e) { print(e); }
print(b[0]);
'''
    assert output(source, mars) == ['INDEX_OUT_OF_RANGE', '3']


def test_list_01_invalid_reservation_size_is_rejected():
    ir = intermediate('let xs: integer[] = [1, 2];\nprint(xs[0]);\n')
    broken = mutate(ir, lambda i: i.opcode is OpCode.LIST_NEW,
                    lambda i: type(i)(OpCode.LIST_NEW, Operand(OperandKind.CONSTANT, -1, INTEGER),
                                      None, i.result, i.source_location))
    generated = generate_mips(broken)
    assert generated.assembly == ''
    assert [d.code for d in generated.diagnostics] == ['MIPS-INVALID-ADDRESS']
    assert generated.diagnostics[0].location is not None


def test_list_01_element_representation_must_match_the_list():
    ir = intermediate('let xs: integer[] = [1, 2];\nlet y: integer = xs[0];\n')
    broken = mutate(ir, lambda i: i.opcode is OpCode.LIST_GET,
                    lambda i: type(i)(OpCode.LIST_GET, i.arg1, i.arg2,
                                      Operand(OperandKind.TEMPORARY, i.result.value, FLOAT,
                                              i.result.lease), i.source_location))
    generated = generate_mips(broken)
    assert not generated.accepted
    assert generated.diagnostics[0].code in ('MIPS-TYPE', 'MIPS-INVALID-IR')

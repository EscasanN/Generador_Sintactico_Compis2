"""OBJ-01..OBJ-03: instances, nominal inheritance and local inheritance."""
import pytest

from pipeline_harness import intermediate, mutate, output, run_source
from src.codegen.ir import OpCode, Operand, OperandKind
from src.mips.generator import generate_mips
from src.mips.layout import PhysicalLayoutPlan
from src.semantic.types import INTEGER

INSTANCES = '''
class Punto {
  let x: integer;
  let y: integer;
  let peso: float = 0.25;
  let activo: boolean;
  function constructor(x: integer, y: integer) { this.x = x; this.y = y; }
  function suma(): integer { return this.x + this.y; }
  function escalar(k: integer) { this.x = this.x * k; this.y = this.y * k; }
}
class Implicito { let n: integer = 41; let s: string = "ok"; }
let a: Punto = new Punto(1, 2);
let b: Punto = new Punto(10, 20);
a.escalar(3);
print(a.suma());
print(b.suma());
print(a.peso + b.peso);
print(a.activo);
b.activo = true;
print(b.activo);
print(a.activo);
let i: Implicito = new Implicito();
i.n = i.n + 1;
print(i.n);
print(i.s);
'''  # 3+6 = 9; 30; 0.5; false (zeroed); true; still false; 42; ok


@pytest.mark.parametrize('banks', [(8, 5), (2, 2)], ids=['full-bank', 'two-registers'])
def test_obj_01_instances(mars, banks):
    assert output(INSTANCES, mars, gpr_count=banks[0], fpr_count=banks[1]) == [
        '9', '30', '0.5', 'false', 'true', 'false', '42', 'ok']


@pytest.mark.parametrize('access', ['print(p.x);', 'p.x = 1;', 'print(p.suma());'],
                         ids=['read', 'write', 'method-this'])
def test_obj_01_null_receivers_raise_null_access(mars, access):
    source = ('class P { let x: integer; function suma(): integer { return this.x; } }\n'
              f'let p: P = null;\n{access}\n')
    result = run_source(source, mars, expect_success=False)
    assert result.returncode == 1 and result.stdout == 'RuntimeError: NULL_ACCESS\n'


def test_obj_01_incoherent_offsets_and_sizes_are_rejected():
    source = 'class P { let x: integer = 1; }\nlet p: P = new P();\nprint(p.x);\n'
    ir = intermediate(source)
    plan = PhysicalLayoutPlan.build(ir.program, ir.layouts)
    size = next(iter(plan.classes.values())).size
    outside = mutate(ir, lambda i: i.opcode is OpCode.FIELD_GET,
                     lambda i: type(i)(OpCode.FIELD_GET, i.arg1, Operand(OperandKind.OFFSET, size),
                                       i.result, i.source_location))
    generated = generate_mips(outside)
    assert [d.code for d in generated.diagnostics] == ['MIPS-INVALID-ADDRESS']
    assert generated.diagnostics[0].location is not None and generated.assembly == ''
    wrong_size = mutate(ir, lambda i: i.opcode is OpCode.OBJECT_NEW,
                        lambda i: type(i)(OpCode.OBJECT_NEW, i.arg1,
                                          Operand(OperandKind.CONSTANT, size + 8, INTEGER),
                                          i.result, i.source_location))
    assert [d.code for d in generate_mips(wrong_size).diagnostics] == ['MIPS-INVALID-IR']
    unknown = mutate(ir, lambda i: i.opcode is OpCode.OBJECT_NEW,
                     lambda i: type(i)(OpCode.OBJECT_NEW, Operand(OperandKind.LABEL, 'Fantasma'),
                                       i.arg2, i.result, i.source_location))
    assert [d.code for d in generate_mips(unknown).diagnostics] == ['MIPS-MISSING-LAYOUT']


INHERITANCE = '''
let orden: string = "";
function traza(s: string): integer { orden = orden + s; return 1; }
class A {
  let a: integer = traza("A");
  function quien(): string { return "A"; }
  function presentar(): string { return "soy " + this.quien(); }
}
class B : A {
  let b: integer = traza("B");
  function quien(): string { return "B"; }
}
class C : B {
  let c: integer = traza("C");
}
let objeto: C = new C();
print(orden);
print(objeto.a + objeto.b + objeto.c);
let comoA: A = objeto;
let comoB: B = objeto;
print(comoA.quien());
print(comoB.quien());
print(objeto.presentar());
'''  # initializers base first: ABC; 3; static resolution by declared type: A, B; "soy A"


def test_obj_02_inheritance(mars):
    assert output(INHERITANCE, mars) == ['ABC', '3', 'A', 'B', 'soy A']


HOMONYMS = '''
function uno(): integer {
  class Caja { let v: integer = 1; let w: integer = 2; let z: integer = 3; }
  let caja: Caja = new Caja();
  return caja.v + caja.w + caja.z;
}
function dos(): string {
  class Caja { let s: string = "dos"; }
  let caja: Caja = new Caja();
  return caja.s;
}
print(uno());
print(dos());
print(uno());
'''


def test_obj_02_homonymous_classes_never_share_a_layout(mars):
    ir = intermediate(HOMONYMS)
    plan = PhysicalLayoutPlan.build(ir.program, ir.layouts)
    boxes = [layout for layout in plan.classes.values() if layout.symbol.name == 'Caja']
    assert len(boxes) == 2 and boxes[0].label != boxes[1].label
    assert boxes[0].symbol.type is not boxes[1].symbol.type
    assert output(HOMONYMS, mars) == ['6', 'dos', '6']


LOCAL = '''
function cero(): integer { return 0; }
let guardado = cero;
function externa(): integer {
  let x: integer = 5;
  class Base {
    let desdeBase: integer = x;
    function leerX(): integer { return x; }
  }
  function interna(): integer {
    let x: integer = 1000;
    class Derivada : Base {
      let propia: integer = x;
    }
    let d: Derivada = new Derivada();
    guardado = d.leerX;
    return d.desdeBase + d.propia;
  }
  let r: integer = interna();
  x = 6;
  return r;
}
print(externa());
print(guardado());
'''  # the inherited initializer reads the base's x (5), not the derived scope's 1000


def test_obj_03_local_inheritance(mars):
    assert output(LOCAL, mars) == ['1005', '6']
    assert output(LOCAL, mars, gpr_count=2, fpr_count=2) == ['1005', '6']

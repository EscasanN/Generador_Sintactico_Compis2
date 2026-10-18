// IDs: PIPE-02, TST-02
// Esperado: REJECT semantic
// La base local A no es la misma declaracion que la A global.
class A { let x: integer = 1; }
function f(): integer {
  let outer: A = new A();
  class A { let y: string = "bad"; }
  class B: A {}
  outer = new B();
  return outer.x;
}
let r = f();

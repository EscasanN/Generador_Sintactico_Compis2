// IDs: CLS-04, CLS-05, TST-02
// Esperado: REJECT semantic
// this fuera de una clase y argumentos extra a un constructor implícito se
// rechazan antes de llegar a la generación de código.
class Simple {
  let valor: integer = 1;
}

let s: Simple = new Simple(5);
let v: integer = this.valor;

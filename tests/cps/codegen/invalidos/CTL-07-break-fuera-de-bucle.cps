// IDs: CTL-07, CTL-08, TST-02
// Esperado: REJECT semantic
// break y continue fuera de un bucle se detienen en la semántica y no llegan a
// la generación de código.
let x: integer = 1;
if (x > 0) {
  break;
}
continue;

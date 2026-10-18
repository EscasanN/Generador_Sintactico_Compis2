// IDs: FUN-04, TST-02
// Esperado: REJECT semantic
// Un return incompatible con la firma impide generar el procedimiento.
function mitad(n: integer): integer {
  return "la mitad";
}

let m: integer = mitad(8);

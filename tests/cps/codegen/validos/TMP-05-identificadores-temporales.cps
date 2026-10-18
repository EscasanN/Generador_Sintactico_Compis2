// IDs: TMP-05, RUN-04, TMP-02
// Esperado: ACCEPT
function calcular(t0: integer): integer {
  let t1: integer = t0 * 2;
  function resultado(): integer { return t0 + t1; }
  return resultado();
}
print(calcular(4));

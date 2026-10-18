// IDs: FUN-07, FUN-08, SYM-05, RUN-03
// Esperado: ACCEPT
function outer(): integer {
  let base: integer = 10;
  function incrementar(): integer { base = base + 1; return base; }
  function intermedia(): integer { return incrementar(); }
  function hermana(): integer {
    let guardada = intermedia;
    return guardada();
  }
  return hermana();
}
print(outer());

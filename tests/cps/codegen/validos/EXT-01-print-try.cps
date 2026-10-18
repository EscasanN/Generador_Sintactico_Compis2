// IDs: EXT-01, EXT-07, PIPE-03
// Esperado: ACCEPT
// print llama al runtime abstracto, try/catch usa instrucciones de alto nivel y
// el código inalcanzable solo produce un warning: el TAC se genera igual.
function primero(valores: integer[]): integer {
  return valores[0];
  print("inalcanzable");
}

let lista: integer[] = [3, 1];
try {
  print(primero(lista));
} catch (error) {
  print("error: " + error);
}

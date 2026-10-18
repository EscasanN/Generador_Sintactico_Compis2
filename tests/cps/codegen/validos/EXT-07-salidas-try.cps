// IDs: EXT-07, CTL-07, CTL-08, FUN-04
// Esperado: ACCEPT
function protegida(b: boolean): integer {
  while (true) {
    try {
      if (b) { return 1; }
      break;
    } catch (err) { return 2; }
  }
  return 3;
}
print(protegida(false));

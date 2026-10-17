// IDs: CTL-01, CTL-02
// Esperado: ACCEPT
// if sin else salta al final cuando la condición es falsa; if/else salta
// sobre la rama else al terminar la rama verdadera.
let n: integer = 5;
let signo: integer = 0;
if (n > 0) {
  signo = 1;
}
if (n % 2 == 0) {
  print("par");
} else {
  print("impar");
}

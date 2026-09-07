// FUN-03: llamada adelantada, recursion directa y recursion mutua.
let cuatroEsPar: boolean = esPar(4);

function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

function esPar(n: integer): boolean {
  if (n == 0) {
    return true;
  }
  return esImpar(n - 1);
}

function esImpar(n: integer): boolean {
  if (n == 0) {
    return false;
  }
  return esPar(n - 1);
}

let seisFactorial: integer = factorial(6);

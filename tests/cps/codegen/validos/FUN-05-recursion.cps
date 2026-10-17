// IDs: FUN-05, FUN-06
// Esperado: ACCEPT
// Recursión directa (factorial y fibonacci llaman a su propia etiqueta) y
// recursión mutua (esPar llama a esImpar, declarada después).
function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

function fibonacci(n: integer): integer {
  if (n < 2) {
    return n;
  }
  return fibonacci(n - 1) + fibonacci(n - 2);
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

let f5: integer = factorial(5);
let fib: integer = fibonacci(7);
let par: boolean = esPar(10);

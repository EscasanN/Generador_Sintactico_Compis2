// IDs: CALL-01, CALL-02, CALL-04, ABI-01, E2E-01
// Esperado: ACCEPT
// Factorial y fibonacci recursivos, recursión mutua y una función de seis
// parámetros (más de los cuatro registros $a0-$a3), también con una llamada
// recursiva como argumento.
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

function sumarSeis(a: integer, b: integer, c: integer, d: integer, e: integer, f: integer): integer {
  return a + b + c + d + e + f;
}

print(factorial(5));
print(fibonacci(10));
print(esPar(10));
print(esImpar(7));
print(sumarSeis(1, 2, 3, 4, 5, 6));
print(sumarSeis(1, factorial(3), 3, 4, 5, 6));

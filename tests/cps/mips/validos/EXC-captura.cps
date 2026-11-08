// IDs: EXC-01, EXC-02, E2E-01
// Esperado: ACCEPT
// Un índice fuera de rango tres frames abajo se captura en el llamador: la
// asignación protegida no ocurre y el programa continúa. Un módulo por cero
// también se captura y la ejecución sigue después de ambos catch.
function leer(xs: integer[], i: integer): integer {
  return xs[i];
}

function nivel2(xs: integer[]): integer {
  return leer(xs, 5) + 1;
}

function nivel1(xs: integer[]): integer {
  return nivel2(xs) * 2;
}

let datos: integer[] = [1, 2, 3];
let resultado: integer = -1;
try {
  resultado = nivel1(datos);
  print("no llega");
} catch (fallo) {
  print("capturado " + fallo);
}
print(resultado);

let divisor: integer = 0;
try {
  print(10 % divisor);
} catch (otro) {
  print("modulo " + otro);
}
print("continua");

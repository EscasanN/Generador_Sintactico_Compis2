// IDs: FUN-01, FUN-02, FUN-03, FUN-04
// Esperado: ACCEPT
// Cada función es un procedimiento con etiqueta propia; los argumentos se
// evalúan de izquierda a derecha (param, param, call) y return respeta la firma.
function sumar(a: integer, b: integer): integer {
  return a + b;
}

function promedio(a: float, b: float): float {
  return (a + b) / 2.0;
}

function saludar(nombre: string) {
  print("hola " + nombre);
  return;
}

let s: integer = sumar(2, 3 * 4);
let pm: float = promedio(1.0, 4);
saludar("mundo");

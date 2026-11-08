// IDs: EXC-01, LIST-01
// Esperado: RUNTIME INDEX_OUT_OF_RANGE
// Un índice igual a la longitud se detecta antes del acceso, aunque ocurra
// dentro de una función: no se lee memoria fuera de la lista.
function leer(xs: integer[], i: integer): integer {
  return xs[i];
}

let datos: integer[] = [1, 2, 3];
print("antes");
print(leer(datos, 3));
print("nunca");

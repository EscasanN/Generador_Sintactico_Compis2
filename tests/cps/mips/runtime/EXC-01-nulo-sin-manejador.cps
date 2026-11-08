// IDs: EXC-01, OBJ-01
// Esperado: RUNTIME NULL_ACCESS
// Leer un campo de una referencia nula es un error controlado del lenguaje,
// no un trap arbitrario de MARS.
class Caja {
  let valor: integer = 1;
}

let caja: Caja = null;
print("antes");
print(caja.valor);
print("nunca");

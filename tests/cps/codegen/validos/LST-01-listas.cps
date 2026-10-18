// IDs: LST-01, LST-02, LST-03, LST-04, EXT-04
// Esperado: ACCEPT
// Creación de listas vacías y no vacías, lectura y escritura por índice,
// índices anidados y foreach traducido a un recorrido indexado.
let vacia = [];
let numeros: integer[] = [5, 6, 7];
let matriz: integer[][] = [[1, 2], [3, 4]];
let primero: integer = numeros[0];
numeros[2] = numeros[0] + numeros[1];
let esquina: integer = matriz[1][0];
matriz[0][1] = esquina;
let total: integer = 0;
foreach (n in numeros) {
  total = total + n;
}

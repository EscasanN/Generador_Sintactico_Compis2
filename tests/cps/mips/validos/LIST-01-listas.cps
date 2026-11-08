// IDs: LIST-01, PIPE-01
// Esperado: ACCEPT
// Listas: vacía, enteros, dobles, booleanos, cadenas, objetos, anidación,
// alias que observa la escritura, foreach y errores de índice/nulo capturados.
let xs: integer[] = [1, 2, 3];
let suma: integer = 0;
foreach (x in xs) {
  suma = suma + x;
}
print(suma);
let vacia = [];
let vueltas: integer = 0;
foreach (v in vacia) {
  vueltas = vueltas + 1;
}
print(vueltas);
let matriz: integer[][] = [[1, 2], [3, 4]];
print(matriz[1][0] + matriz[0][1]);
let alias: integer[] = xs;
alias[0] = 10;
print(xs[0]);
let dobles: float[] = [1.25, 2.5];
print(dobles[0] + dobles[1]);
let banderas: boolean[] = [true, false, true];
print(banderas[1]);
print(banderas[2]);
let palabras: string[] = ["uno", "dos"];
palabras[1] = palabras[0] + "!";
print(palabras[1]);
class Nodo {
  let valor: integer;
  function constructor(v: integer) {
    this.valor = v;
  }
}
let nodos: Nodo[] = [new Nodo(4), new Nodo(5)];
print(nodos[0].valor + nodos[1].valor);
print(xs);
let fuera: integer = 3;
try {
  print(xs[fuera]);
} catch (e) {
  print(e);
}
let negativo: integer = -1;
try {
  print(xs[negativo]);
} catch (e) {
  print(e);
}
try {
  xs[fuera] = 1;
} catch (e) {
  print("store " + e);
}
let nula: integer[] = null;
try {
  print(nula[0]);
} catch (e) {
  print(e);
}
print(xs[0] + xs[1] + xs[2]);

// Extensiones: %, strings, null, herencia, recursion mutua, foreach y catch.
class Padre {
  let valor: integer;
}

class Hijo : Padre {
}

function par(n: integer): boolean {
  if (n == 0) {
    return true;
  }
  return impar(n - 1);
}

function impar(n: integer): boolean {
  if (n == 0) {
    return false;
  }
  return par(n - 1);
}

let mensaje: string = "todo " + "funciona";
let residuo: integer = 7 % 2;
let opcional: Hijo = null;
let numeros: integer[] = [1, 2, 3];

foreach (numero in numeros) {
  let copia: integer = numero;
  print(copia);
}

try {
  print(mensaje);
} catch (error) {
  let detalle: string = "error: " + error;
  print(detalle);
}

let resultado: boolean = par(residuo);

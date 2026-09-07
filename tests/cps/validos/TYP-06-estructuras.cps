// TYP-06: listas y campos conservan un tipo valido.
class Caja {
  let valor = 1;
}

let caja = new Caja();
let numeros: integer[] = [caja.valor, 2, 3];

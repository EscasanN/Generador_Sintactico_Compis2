// CLS-01: los atributos y metodos accedidos existen.
class Punto {
  let x: integer;
  let y: integer;

  function constructor(x: integer, y: integer) {
    this.x = x;
    this.y = y;
  }

  function suma(): integer {
    return this.x + this.y;
  }
}

let punto = new Punto(2, 3);
let coordenada: integer = punto.x;
let total: integer = punto.suma();

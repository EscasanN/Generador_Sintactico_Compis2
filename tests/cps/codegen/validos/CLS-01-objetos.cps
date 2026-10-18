// IDs: CLS-01, CLS-02, CLS-03, CLS-04, CLS-05
// Esperado: ACCEPT
// new reserva el objeto y llama al constructor con this oculto; los campos se
// leen/escriben por offset y los métodos reciben el receptor como primer param.
class Punto {
  let x: integer;
  let y: integer;

  function constructor(x: integer, y: integer) {
    this.x = x;
    this.y = y;
  }

  function mover(dx: integer, dy: integer) {
    this.x = this.x + dx;
    this.y = this.y + dy;
  }

  function distanciaManhattan(): integer {
    return this.x + this.y;
  }
}

class Vacia {
  let creada: boolean = true;
}

let p: Punto = new Punto(1, 2);
p.mover(3, 4);
let d: integer = p.distanciaManhattan();
let v: Vacia = new Vacia();
let ok: boolean = v.creada;

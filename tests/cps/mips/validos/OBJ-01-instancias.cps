// IDs: OBJ-01, PIPE-01
// Esperado: ACCEPT
// Constructores explícito e implícito, campos de todos los tipos, this y
// métodos; dos instancias conservan valores independientes. Un receptor nulo
// produce NULL_ACCESS, también dentro de un método llamado sobre null.
class Punto {
  let x: integer;
  let y: integer;
  let etiqueta: string = "p";
  let activo: boolean = true;
  let peso: float = 1.5;

  function constructor(x: integer, y: integer) {
    this.x = x;
    this.y = y;
  }

  function suma(): integer {
    return this.x + this.y;
  }

  function mover(d: integer) {
    this.x = this.x + d;
  }
}

class Vacia {
  let creada: boolean = true;
}

let a: Punto = new Punto(1, 2);
let b: Punto = new Punto(10, 20);
a.mover(4);
print(a.suma());
print(b.suma());
print(a.etiqueta + b.etiqueta);
print(a.activo);
print(a.peso + b.peso);
let v: Vacia = new Vacia();
print(v.creada);
print(a);
let nulo: Punto = null;
try {
  print(nulo.x);
} catch (e) {
  print("lectura " + e);
}
try {
  nulo.x = 3;
} catch (e) {
  print("escritura " + e);
}
try {
  nulo.mover(1);
} catch (e) {
  print("metodo " + e);
}

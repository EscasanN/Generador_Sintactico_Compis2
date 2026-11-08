// IDs: OBJ-01, OBJ-03, METHOD-01, E2E-01
// Esperado: ACCEPT
// Dos instancias conservan campos independientes. Una clase base declarada en
// la función exterior y su derivada en una función anidada usan cada una su
// propio entorno; el método ligado escapa y sigue viendo esos entornos.
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

function cero(): integer {
  return 0;
}

let metodo = cero;

function taller(factor: integer): integer {
  class Pieza {
    let medida: integer = factor * 2;
    function area(): integer {
      return this.medida * factor;
    }
  }
  function linea(extra: integer): integer {
    class PiezaLarga : Pieza {
      let largo: integer = extra;
      function total(): integer {
        return this.area() + this.largo;
      }
    }
    let pieza: PiezaLarga = new PiezaLarga();
    metodo = pieza.total;
    return pieza.total();
  }
  return linea(5);
}

let p1: Punto = new Punto(1, 2);
let p2: Punto = new Punto(10, 20);
p1.x = 5;
print(p1.suma());
print(p2.suma());
print(taller(3));
print(metodo());

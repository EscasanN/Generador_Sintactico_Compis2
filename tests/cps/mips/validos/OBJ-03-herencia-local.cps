// IDs: OBJ-03, METHOD-01, PIPE-01
// Esperado: ACCEPT
// Herencia local: la base y la derivada se declaran en ámbitos distintos y
// cada inicializador usa el entorno de su propia clase. La construcción más
// anidada funciona y los métodos ligados escapan de su creador.
function cero(): integer {
  return 0;
}

let guardado = cero;

function fabrica(base: integer): integer {
  let extra: integer = base * 2;
  class Base {
    let valor: integer = base + extra;
    function leer(): integer {
      return this.valor + extra;
    }
  }
  function nivel(): integer {
    let otro: integer = 100;
    class Derivada : Base {
      let mas: integer = otro;
      function todo(): integer {
        return this.leer() + this.mas;
      }
    }
    let d: Derivada = new Derivada();
    guardado = d.todo;
    extra = 10;
    return d.todo();
  }
  return nivel();
}

print(fabrica(1));
print(guardado());

function crear(paso: integer) {
  class Contador {
    let n: integer = 0;
    function avanzar(): integer {
      this.n = this.n + paso;
      return this.n;
    }
  }
  let c: Contador = new Contador();
  guardado = c.avanzar;
}

crear(5);
print(guardado());
print(guardado());
crear(7);
print(guardado());

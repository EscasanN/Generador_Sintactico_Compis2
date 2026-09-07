// CLS-03: this se usa dentro del entorno de clase.
class Acumulador {
  let total: integer;

  function constructor() {
    this.total = 0;
  }

  function incrementar(): integer {
    this.total = this.total + 1;
    return this.total;
  }
}

let acumulador = new Acumulador();
print(acumulador.incrementar());

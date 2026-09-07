// CLS-02: constructor explicito correcto e implicito de aridad cero.
class ConConstructor {
  let valor: integer;

  function constructor(valor: integer) {
    this.valor = valor;
  }
}

class SinConstructor {
  let nombre: string = "vacio";
}

let primero = new ConConstructor(5);
let segundo = new SinConstructor();

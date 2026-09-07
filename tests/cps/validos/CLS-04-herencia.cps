// CLS-04: superclase posterior, miembro heredado y widening de clase.
class Hija : Base {
  function leer(): integer {
    return this.valor;
  }
}

class Base {
  let valor: integer;
}

let hija = new Hija();
let comoBase: Base = hija;
let heredado: integer = hija.leer();

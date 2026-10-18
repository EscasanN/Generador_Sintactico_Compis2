// IDs: CLS-04, FUN-07, FUN-08, TST-01
// Esperado: ACCEPT
// El receptor se conserva en el entorno léxico de la función anidada.
class Contador {
  let valor: integer = 0;

  function siguiente(): integer {
    function leer(): integer {
      return this.valor;
    }
    return leer() + 1;
  }
}

let c: Contador = new Contador();
let n: integer = c.siguiente();

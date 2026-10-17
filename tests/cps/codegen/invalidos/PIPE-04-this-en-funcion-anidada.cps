// IDs: PIPE-04, OUT-05, TST-02
// Esperado: REJECT codegen IRGEN-THIS-UNAVAILABLE
// Limitación documentada del bloque 3: this no se captura dentro de una
// función anidada en un método. El rechazo es explícito, con código y ubicación.
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

// IDs: CLS-03, CLS-04, CLS-06, FUN-07, FUN-08, EXT-05
// Esperado: ACCEPT
function calcular(): integer {
  let inicial: integer = 7;
  class Base {
    let valor: integer = inicial;
    function leer(): integer { return valor; }
  }
  function derivar(): integer {
    let extra: integer = 2;
    class Hija: Base { let delta: integer = extra; }
    function construir(): integer {
      let item = new Hija();
      return item.leer() + item.delta;
    }
    return construir();
  }
  return derivar();
}
print(calcular());

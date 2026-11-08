// IDs: ENV-01, ENV-02, ENV-03, E2E-01
// Esperado: ACCEPT
// Closures que sobreviven a su creador: dos funciones hermanas comparten la
// misma celda capturada, y un segundo creador obtiene un estado independiente.
// La captura a dos niveles sigue el enlace de acceso.
function cero(): integer {
  return 0;
}

let incrementar = cero;
let consultar = cero;

function crear(inicio: integer) {
  let valor: integer = inicio;
  function mas(): integer {
    valor = valor + 1;
    return valor;
  }
  function ver(): integer {
    return valor;
  }
  incrementar = mas;
  consultar = ver;
}

function externo(a: integer): integer {
  function medio(): integer {
    function interno(): integer {
      return a * 10;
    }
    return interno();
  }
  return medio();
}

crear(0);
print(incrementar());
print(incrementar());
print(consultar());
let primero = incrementar;
crear(100);
print(incrementar());
print(primero());
print(consultar());
print(externo(4));

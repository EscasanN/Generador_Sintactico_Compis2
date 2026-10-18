// IDs: FUN-07, FUN-08, FUN-09, SYM-05, RUN-03
// Esperado: ACCEPT
// Funciones anidadas que capturan variables a uno y dos niveles. La captura se
// resuelve por el enlace de acceso (env), nunca por el enlace de control.
function contador(inicio: integer): integer {
  let cuenta: integer = inicio;
  function incrementar(paso: integer): integer {
    cuenta = cuenta + paso;
    function doble(): integer {
      return cuenta * 2;
    }
    return doble();
  }
  incrementar(1);
  return incrementar(2);
}

let resultado: integer = contador(10);

// FUN-04: una funcion anidada captura el entorno de definicion.
function exterior(): integer {
  let base: integer = 10;

  function interior(): integer {
    return base + 1;
  }

  return interior();
}

let resultado: integer = exterior();

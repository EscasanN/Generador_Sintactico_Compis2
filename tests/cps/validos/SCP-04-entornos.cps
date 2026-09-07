// SCP-04: se crean entornos global, de funcion, clase y bloque.
function identidad(valor: integer): integer {
  let copia: integer = valor;
  return copia;
}

class Contenedor {
  let valor: integer;
  function guardar(valor: integer) {
    this.valor = valor;
  }
}

{
  let temporal: integer = identidad(3);
  print(temporal);
}

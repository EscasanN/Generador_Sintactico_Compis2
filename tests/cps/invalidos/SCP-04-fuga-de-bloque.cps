// SCP-04 invalido: un bloque no filtra sus simbolos al scope de funcion.
function obtener(): integer {
  if (true) {
    let interno: integer = 1;
  }
  return interno;
}

// FUN-04 invalido: la funcion interna intenta capturar un nombre inexistente.
function exterior(): integer {
  function interior(): integer {
    return ausente;
  }

  return interior();
}

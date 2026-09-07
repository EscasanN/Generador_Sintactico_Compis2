// FUN-03 invalido: un simbolo local oculta la referencia recursiva valida.
function factorial(n: integer): integer {
  let factorial: integer = 1;
  return factorial(n - 1);
}

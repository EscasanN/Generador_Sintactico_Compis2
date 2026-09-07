// FUN-05: funciones distintas coexisten en el mismo scope.
function uno(): integer {
  return 1;
}

function dos(): integer {
  return 2;
}

let suma: integer = uno() + dos();

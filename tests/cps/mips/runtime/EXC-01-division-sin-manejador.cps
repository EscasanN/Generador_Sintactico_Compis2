// IDs: EXC-01, EXC-03
// Esperado: RUNTIME DIV_ZERO
// Sin manejador activo el error imprime RuntimeError: CODIGO y termina con
// código 1. Los manejadores retirados por return o por terminar su try no
// capturan nada: el error no salta a un catch de un ámbito ya cerrado.
let cero: integer = 0;

function f(): integer {
  try {
    return 1;
  } catch (e) {
    return 2;
  }
}

print(f());
try {
  print("protegido");
} catch (e) {
  print("nunca");
}
print(4 / cero);
print("nunca");

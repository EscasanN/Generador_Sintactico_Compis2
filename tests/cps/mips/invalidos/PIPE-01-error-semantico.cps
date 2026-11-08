// IDs: PIPE-01, STR-01
// Esperado: REJECT semantic
// string + integer no es una concatenación válida: el error de tipos impide
// llegar al TAC y al backend.
let mensaje: string = "valor: " + 1;
print(mensaje);

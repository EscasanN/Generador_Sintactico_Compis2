// IDs: STR-01, EXC-01
// Esperado: RUNTIME NULL_ACCESS
// Una cadena sin inicializar es null: no se trata como "" ni se desreferencia.
let sinValor: string;
print("antes");
print(sinValor + "x");
print("nunca");

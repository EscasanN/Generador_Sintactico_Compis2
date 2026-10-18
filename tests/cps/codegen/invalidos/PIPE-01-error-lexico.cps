// IDs: PIPE-01, OUT-05, TST-02
// Esperado: REJECT syntax
// Un carácter que ningún token reconoce detiene la compilación en el frontend:
// no se ejecuta la semántica ni se genera TAC.
let precio: integer = 10 # 2;

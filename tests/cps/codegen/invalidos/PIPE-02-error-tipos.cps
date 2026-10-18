// IDs: PIPE-02, EXP-06, TST-02
// Esperado: REJECT semantic
// Escribir una constante después de declararla es un error semántico; por eso
// nunca se genera la copia correspondiente en TAC.
const LIMITE: integer = 10;
LIMITE = 20;

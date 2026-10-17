// IDs: PIPE-01, OUT-05, TST-02
// Esperado: REJECT syntax
// Falta la expresión del inicializador: el parser rechaza el programa y no se
// llega al análisis semántico ni a la generación de código.
let x: integer = 1;
let y: integer = ;

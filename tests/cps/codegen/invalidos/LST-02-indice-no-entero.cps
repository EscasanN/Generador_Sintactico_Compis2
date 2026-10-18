// IDs: LST-01, LST-02, LST-03, TST-02
// Esperado: REJECT semantic
// Un índice que no es integer, una lista heterogénea y un store incompatible
// se detienen en la semántica: no se emite list_get ni list_set.
let numeros: integer[] = [1, 2, 3];
let a: integer = numeros["0"];
let mezcla: integer[] = [1, "dos"];
numeros[0] = true;

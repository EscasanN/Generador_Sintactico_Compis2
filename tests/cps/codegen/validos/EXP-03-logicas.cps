// IDs: EXP-03, EXP-04, EXP-07, EXT-03, TMP-04
// Esperado: ACCEPT
// && y || se traducen con cortocircuito real (el lado derecho queda detrás de
// un salto), cada comparador produce un boolean y el ternario evalúa una rama.
let a: integer = 4;
let b: integer = 9;
let igual: boolean = a == b;
let distinto: boolean = a != b;
let menor: boolean = a < b;
let menorIgual: boolean = a <= b;
let mayor: boolean = a > b;
let mayorIgual: boolean = a >= b;
let ambos: boolean = a < b && b > 0;
let alguno: boolean = a > b || b != 0;
let combinado: boolean = (a < b || a == 0) && !(b == 0);
let maximo: integer = a > b ? a : b;

// IDs: TMP-01, TMP-02, TMP-03, TMP-04, TMP-05, RUN-04
// Esperado: ACCEPT
// Expresiones largas reutilizan los mismos temporales una vez consumidos: el
// frame reserva el pico de temporales vivos, no todos los creados.
let a: integer = 1;
let b: integer = 2;
let c: integer = 3;
let d: integer = 4;
let r1: integer = (a + b) * (c + d);
let r2: integer = (a * b) + (c * d) - (a - d);
let r3: integer = ((a + b) + (c + d)) * ((a - b) - (c - d));
let r4: boolean = a < b ? c > d : a == d;

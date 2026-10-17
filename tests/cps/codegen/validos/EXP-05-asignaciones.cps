// IDs: EXP-05, EXP-06, EXP-08, SYM-03, SYM-06
// Esperado: ACCEPT
// Las declaraciones usan el Symbol resuelto (el shadowing escribe en slots
// distintos), una constante se copia una sola vez y las asignaciones a campo e
// índice usan field_set y list_set.
class Caja {
  let contenido: integer;
}

const LIMITE: integer = 10;
let total: integer = 0;
total = total + LIMITE;
{
  let total: integer = 5;
  total = total * 2;
}
let caja: Caja = new Caja();
caja.contenido = total;
let valores: integer[] = [1, 2, 3];
valores[1] = caja.contenido + LIMITE;

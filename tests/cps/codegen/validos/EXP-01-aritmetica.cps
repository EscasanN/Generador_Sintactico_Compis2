// IDs: EXP-01, EXP-02, EXT-02, EXT-06
// Esperado: ACCEPT
// Precedencia y asociatividad salen del árbol: MUL antes que ADD y la resta
// asocia a la izquierda. Incluye unarios, módulo, conversión int->float y null.
class Nodo {
  let valor: integer;
}

let x: integer = 7;
let y: integer = 3;
let z: integer = 2;
let suma: integer = x + y * z;
let agrupada: integer = (x + y) * z;
let izquierda: integer = x - y - z;
let cociente: integer = x / y;
let resto: integer = x % y;
let negativo: integer = -x;
let mixto: float = x * 1.5;
let activo: boolean = true;
let inactivo: boolean = !activo;
let vacio: Nodo = null;

// IDs: REG-01, REG-02, REG-03, CALL-03, E2E-01
// Esperado: ACCEPT
// Expresiones anidadas a la derecha mantienen vivos más valores que registros
// asignables: getReg derrama y recarga sin perder ninguno. La llamada en medio
// de una suma conserva los valores vivos alrededor del jal.
function doble(n: integer): integer {
  return n * 2;
}

let a: integer = 1;
let b: integer = 2;
let c: integer = 3;
let d: integer = 4;
let e: integer = 5;
let f: integer = 6;
let g: integer = 7;
let h: integer = 8;
let i: integer = 9;
let j: integer = 10;

print(a + (b + (c + (d + (e + (f + (g + (h + (i + j)))))))));
print(a * b + c * d + e * f + g * h + i * j);
print(a - (b - (c - (d - (e - (f - (g - (h - (i - j)))))))));
print(a + b * c + doble(d) + e);

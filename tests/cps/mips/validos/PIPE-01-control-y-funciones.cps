// IDs: PIPE-01
// Esperado: ACCEPT
// Cortocircuito con efectos, ternario, las cuatro formas de for, while,
// do-while, switch con caída y discriminante evaluado una vez, recursión,
// seis argumentos y aritmética entera/doble con negativos.
let contador: integer = 0;

function efecto(): boolean {
  contador = contador + 1;
  return true;
}

let a: boolean = false && efecto();
let b: boolean = true || efecto();
let c: boolean = true && efecto();
print(contador);
print(a || b);
print(c ? "si" : "no");
let i: integer = 0;
while (i < 3) {
  i = i + 1;
}
print(i);
do {
  i = i - 1;
} while (i > 0);
print(i);
let total: integer = 0;
for (let k: integer = 0; k < 5; k = k + 1) {
  if (k == 1) {
    continue;
  }
  total = total + k;
}
print(total);
// Los for sin condición viven en su propia función: ver INC-B3-01 en
// docs/proyecto3/entrega-bloque3-dulce.md (defecto del TAC del Proyecto 2).
function sinCondicion(): integer {
  let n: integer = 0;
  for (;;) {
    n = n + 1;
    if (n == 4) {
      break;
    }
  }
  return n;
}

function soloActualizacion(): integer {
  let r: integer = 0;
  for (; ; r = r + 1) {
    if (r == 3) {
      break;
    }
  }
  return r;
}

print(sinCondicion());
let m: integer = 0;
for (; m < 2;) {
  m = m + 1;
}
print(m + soloActualizacion());
let veces: integer = 0;

function discriminante(): boolean {
  veces = veces + 1;
  return true;
}

switch (discriminante()) {
  case false:
    print("uno");
  case true:
    print("dos");
  case 1 < 2:
    print("tres");
  default:
    print("defecto");
}
print(veces);

function fib(x: integer): integer {
  if (x < 2) {
    return x;
  }
  return fib(x - 1) + fib(x - 2);
}

print(fib(10));

function seis(p1: integer, p2: integer, p3: integer, p4: integer, p5: integer, p6: integer): integer {
  return p1 + p2 + p3 + p4 + p5 + p6;
}

print(seis(1, 2, 3, 4, 5, 6));
let neg: integer = -7;
print(neg / 2);
print(neg % 2);
print(2.5 * 2.0);

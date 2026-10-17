// IDs: CTL-03, CTL-04, CTL-05, CTL-07, CTL-08
// Esperado: ACCEPT
// while, do-while y las cuatro formas de for. continue va a la condición en
// while/do-while y a la actualización en for; break sale del bucle más cercano.
let i: integer = 0;
while (i < 10) {
  i = i + 1;
  if (i == 2) {
    continue;
  }
  if (i == 8) {
    break;
  }
}

let j: integer = 0;
do {
  j = j + 1;
  if (j == 1) {
    continue;
  }
} while (j < 3);

for (let k: integer = 0; k < 3; k = k + 1) {
  for (let m: integer = 0; m < 3; m = m + 1) {
    if (m == 1) {
      break;
    }
    if (k == 1) {
      continue;
    }
  }
}

let p: integer = 0;
for (; p < 2;) {
  p = p + 1;
}
for (p = 0; ; p = p + 1) {
  if (p > 2) {
    break;
  }
}
for (;;) {
  break;
}

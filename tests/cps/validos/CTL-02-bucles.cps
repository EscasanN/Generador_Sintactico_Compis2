// CTL-02: break y continue viven dentro de bucles; foreach tipa su iterador.
while (true) {
  break;
}

for (let i: integer = 0; i < 2; i = i + 1) {
  continue;
}

let valores: integer[] = [1, 2, 3];
foreach (valor in valores) {
  let copia: integer = valor;
  print(copia);
}

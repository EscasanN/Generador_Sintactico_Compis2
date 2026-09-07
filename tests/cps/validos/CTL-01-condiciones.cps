// CTL-01: todas las construcciones reciben condiciones booleanas.
if (true) {
  print(1);
} else {
  print(0);
}

while (true) {
  break;
}

do {
  break;
} while (true);

for (let i: integer = 0; i < 1; i = i + 1) {
  continue;
}

switch (true) {
  case true:
    print(1);
  default:
    print(0);
}

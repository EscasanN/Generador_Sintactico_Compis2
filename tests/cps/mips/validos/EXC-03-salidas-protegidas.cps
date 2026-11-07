// IDs: EXC-03, PIPE-01
// Esperado: ACCEPT
// return, break y continue dentro de try retiran exactamente sus manejadores:
// un error posterior llega al catch vigente, nunca al de un ámbito terminado.
let cero: integer = 0;

function conReturn(b: boolean): integer {
  try {
    if (b) {
      return 1;
    }
  } catch (e) {
    return -1;
  }
  return 2;
}

print(conReturn(true));
print(conReturn(false));
try {
  print(10 / cero);
} catch (e) {
  print("principal " + e);
}
let k: integer = 0;
let pasos: integer = 0;
while (k < 5) {
  k = k + 1;
  try {
    if (k == 2) {
      continue;
    }
    if (k == 4) {
      break;
    }
    pasos = pasos + 1;
  } catch (e) {
    print("nunca");
  }
}
print(k);
print(pasos);
try {
  for (let j: integer = 0; j < 3; j = j + 1) {
    try {
      if (j == 1) {
        break;
      }
    } catch (e) {
      print("interno");
    }
  }
  print(5 / cero);
} catch (e) {
  print("externo " + e);
}

function anidada(): integer {
  try {
    try {
      return 7;
    } catch (e) {
      return 8;
    }
  } catch (e) {
    return 9;
  }
}

print(anidada());
try {
  print(1 / cero);
} catch (e) {
  print("final " + e);
}

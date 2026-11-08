// IDs: EXC-01, EXC-02, PIPE-01
// Esperado: ACCEPT
// Errores runtime (división y módulo por cero, enteros y dobles, índice) se
// capturan en el llamador aunque se produzcan varios frames más abajo; un
// catch que falla llega al manejador exterior y el programa continúa.
function dividir(a: integer, b: integer): integer {
  return a / b;
}

function profundo(n: integer): integer {
  let local: integer = n * 10;
  if (n == 0) {
    return dividir(local, n);
  }
  return profundo(n - 1) + local;
}

function leer(xs: integer[], i: integer): integer {
  return xs[i];
}

let cero: integer = 0;
let ceroF: float = 0.0;
try {
  print(dividir(7, 0));
} catch (e) {
  print("entero " + e);
}
try {
  print(7 % cero);
} catch (e) {
  print("modulo " + e);
}
try {
  print(1.5 / ceroF);
} catch (e) {
  print("doble " + e);
}
try {
  print(1.5 % ceroF);
} catch (e) {
  print("resto " + e);
}
try {
  print(profundo(4));
} catch (e) {
  print("profundo " + e);
}
let lista: integer[] = [1, 2];
try {
  print(leer(lista, 2));
} catch (e) {
  print("indice " + e);
}
try {
  try {
    print(dividir(1, cero));
  } catch (e) {
    print("interno " + e);
    print(leer(lista, 5));
  }
} catch (e2) {
  print("externo " + e2);
}

function protegida(): string {
  try {
    let valor: integer = leer(lista, 9);
    return "valor";
  } catch (e) {
    return "capturado " + e;
  }
}

print(protegida());
let i: integer = 0;
let capturas: integer = 0;
while (i < 50) {
  try {
    let r: integer = dividir(i, cero);
  } catch (e) {
    capturas = capturas + 1;
  }
  i = i + 1;
}
print(capturas);
print(dividir(10, 2));

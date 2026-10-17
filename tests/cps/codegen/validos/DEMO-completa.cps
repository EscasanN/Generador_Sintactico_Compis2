// IDs: PIPE-05, OUT-01, OUT-03, OUT-04, IDE-01, TST-01
// Esperado: ACCEPT
// Demostración integral de la generación de código intermedio: expresiones,
// control de flujo, funciones recursivas, closures, clases con constructor,
// métodos y this, listas, foreach, switch y reciclaje de temporales.

class Cuenta {
  let titular: string;
  let saldo: integer;

  function constructor(titular: string, saldo: integer) {
    this.titular = titular;
    this.saldo = saldo;
  }

  function depositar(monto: integer): integer {
    this.saldo = this.saldo + monto;
    return this.saldo;
  }
}

class CuentaAhorro : Cuenta {
  let tasa: float = 0.05;

  function interes(): float {
    return this.saldo * this.tasa;
  }
}

function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

function acumulador(inicio: integer): integer {
  let total: integer = inicio;
  function sumar(valor: integer): integer {
    total = total + valor;
    return total;
  }
  sumar(5);
  return sumar(10);
}

// Expresiones y temporales.
let a: integer = 6;
let b: integer = 4;
let expresion: integer = (a + b) * (a - b) / 2 % 7;
let enRango: boolean = a > 0 && b < 10 || !(a == b);
let mayor: integer = a > b ? a : b;

// Funciones, recursión y closures.
let fact: integer = factorial(5);
let acumulado: integer = acumulador(1);

// Objetos, herencia y métodos.
let cuenta: CuentaAhorro = new CuentaAhorro();
cuenta.depositar(100);
let interes: float = cuenta.interes();
let corriente: Cuenta = new Cuenta("Ana", 50);
let saldo: integer = corriente.depositar(25);

// Listas y recorridos.
let numeros: integer[] = [3, 1, 4, 1, 5];
numeros[0] = numeros[1] + numeros[2];
let suma: integer = 0;
foreach (n in numeros) {
  if (n == 1) {
    continue;
  }
  suma = suma + n;
}

let i: integer = 0;
while (i < 3) {
  i = i + 1;
}
do {
  i = i - 1;
} while (i > 0);
for (let k: integer = 0; k < 5; k = k + 1) {
  if (k == 3) {
    break;
  }
  print(k);
}

switch (suma % 3 == 0) {
  case true:
    print("multiplo de tres");
  case suma > 10:
    print("mayor que diez");
  default:
    print("otro resto");
}

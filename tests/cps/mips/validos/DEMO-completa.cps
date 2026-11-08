// IDs: E2E-01, PIPE-01, NUM-01, CALL-04, ENV-02, OBJ-01, LIST-01, STR-01, EXC-02
// Esperado: ACCEPT
// Demostración integral del backend MIPS: aritmética, control, recursión,
// closure que sobrevive a su creador, objetos, listas, cadenas y un error
// capturado en el llamador. Cada línea impresa tiene su valor en el oráculo.
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

function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

function cero(): integer {
  return 0;
}

let siguiente = cero;

function crearContador(inicio: integer) {
  let cuenta: integer = inicio;
  function avanzar(): integer {
    cuenta = cuenta + 1;
    return cuenta;
  }
  siguiente = avanzar;
}

function dividir(a: integer, b: integer): integer {
  return a / b;
}

print((2 + 3) * (7 - 1));
print(factorial(5));

crearContador(10);
print(siguiente());
print(siguiente());

let cuenta: Cuenta = new Cuenta("Ana", 50);
print(cuenta.depositar(25));
print(cuenta.titular + " tiene " + "saldo");

let numeros: integer[] = [3, 1, 4, 1, 5];
let suma: integer = 0;
foreach (n in numeros) {
  suma = suma + n;
}
print(suma);

let i: integer = 0;
while (i < 3) {
  i = i + 1;
}
print(i);

try {
  print(dividir(7, 0));
} catch (error) {
  print("capturado " + error);
}
print("fin");

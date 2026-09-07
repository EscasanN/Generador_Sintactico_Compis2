// Programa integral para la presentación y para pruebas manuales del IDE.
class BaseCounter {
  let value: integer;

  function label(): string {
    return "counter";
  }
}

class Counter : BaseCounter {
  function constructor(initial: integer) {
    this.value = initial;
  }

  function description(): string {
    return this.label() + " ready";
  }

  function isCurrentValueEven(): boolean {
    return isEven(this.value);
  }
}

// Las firmas globales se conocen antes de recorrer los cuerpos.
function isEven(n: integer): boolean {
  if (n == 0) {
    return true;
  }
  return isOdd(n - 1);
}

function isOdd(n: integer): boolean {
  if (n == 0) {
    return false;
  }
  return isEven(n - 1);
}

let counter = new Counter(4);
let asBase: BaseCounter = counter;
let optionalCounter: Counter = null;
let remainder: integer = counter.value % 2;
let values: integer[] = [1, 2, 3];

foreach (value in values) {
  let copy: integer = value;
  print(copy);
}

try {
  print(counter.description());
} catch (error) {
  let message: string = "error: " + error;
  print(message);
}

switch (counter.isCurrentValueEven()) {
  case true:
    print(asBase.label());
  default:
    print(remainder);
}

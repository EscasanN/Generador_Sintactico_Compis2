// IDs: CLS-06, EXT-05
// Esperado: ACCEPT
// Los campos heredados preceden a los propios y conservan su offset; un método
// de la base se invoca por su etiqueta (tipo estático, sin vtables).
class Animal {
  let nombre: string;
  let patas: integer = 4;

  function describir(): string {
    return this.nombre;
  }
}

class Perro : Animal {
  let raza: string;

  function constructor(nombre: string, raza: string) {
    this.nombre = nombre;
    this.raza = raza;
  }

  function ficha(): string {
    return this.describir() + " (" + this.raza + ")";
  }
}

let perro: Perro = new Perro("Fido", "beagle");
let texto: string = perro.ficha();
let patas: integer = perro.patas;

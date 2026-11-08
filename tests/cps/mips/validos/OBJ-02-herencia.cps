// IDs: OBJ-02, PIPE-01
// Esperado: ACCEPT
// Herencia nominal: campos base y derivados con inicializadores base primero;
// los métodos usan la resolución estática del TAC (por el tipo declarado), sin
// despacho dinámico añadido por el backend. Dos clases locales homónimas no
// comparten layout.
class Animal {
  let nombre: string = "animal";
  let patas: integer = 4;

  function hablar(): string {
    return "...";
  }

  function describir(): string {
    return this.nombre + " " + this.hablar();
  }
}

class Perro : Animal {
  let raza: string = "mestizo";

  function hablar(): string {
    return "guau";
  }
}

class Cachorro : Perro {
  let edad: integer = 1;
}

let p: Perro = new Perro();
let base: Animal = p;
print(p.hablar());
print(base.hablar());
print(p.describir());
print(p.raza + " " + p.nombre);
let c: Cachorro = new Cachorro();
print(c.patas + c.edad);
print(c.nombre);

function uno(): integer {
  class Caja {
    let v: integer = 1;
    let w: integer = 2;
  }
  let caja: Caja = new Caja();
  return caja.v + caja.w;
}

function dos(): string {
  class Caja {
    let s: string = "dos";
  }
  let caja: Caja = new Caja();
  return caja.s;
}

print(uno());
print(dos());

// Programa para demostrar varias categorias de diagnostico en una sola corrida.

// TYPE: inicializador incompatible.
let numero: integer = "texto";

// SCOPE: identificador no declarado.
let copia: integer = ausente;

// FUNCTION: retorno y aridad incompatibles.
function retornoIncorrecto(): integer {
  return "texto";
}

function sumar(a: integer, b: integer): integer {
  return a + b;
}

let suma: integer = sumar(1);

// CONTROL_FLOW: transferencia fuera de un bucle.
break;

// CLASS: acceso a un miembro inexistente.
class Caja {
}

let caja = new Caja();
let faltante = caja.noExiste;

// ARRAY: elementos sin tipo comun.
let mezcla = [1, "dos"];

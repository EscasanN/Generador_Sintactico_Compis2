// IDs: PIPE-02, IDE-03, OUT-05, TST-02
// Esperado: REJECT semantic
// Demostración fallida: el programa es sintácticamente correcto pero tiene
// errores semánticos de tipo, de alcance y de llamada. Ninguna fase posterior
// se ejecuta, así que no existe TAC ni tabla extendida.
function doble(n: integer): integer {
  return n * 2;
}

let contador: integer = "cero";
let resultado: integer = doble(1, 2);
print(noDeclarada);

// IDs: PIPE-01
// Esperado: REJECT codegen IRGEN-UNSUPPORTED-NODE
// La semántica acepta el acceso estático C.campo pero el generador de TAC no
// lo traduce: el rechazo de esa fase tampoco produce MIPS.
class Configuracion {
  let nivel: integer;
}

let nivel: integer = Configuracion.nivel;
print(nivel);

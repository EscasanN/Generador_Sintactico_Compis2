// IDs: PIPE-04, EXT-08, OUT-05, TST-02
// Esperado: REJECT codegen IRGEN-UNSUPPORTED-NODE
// La semántica acepta el acceso estático C.campo, pero el generador no tiene
// una traducción para él: la compilación se rechaza con un diagnóstico IR y
// nunca se publica TAC parcial.
class Configuracion {
  let nivel: integer;
}

let nivel: integer = Configuracion.nivel;

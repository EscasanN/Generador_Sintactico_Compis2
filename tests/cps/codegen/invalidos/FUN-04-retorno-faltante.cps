// IDs: FUN-04, PIPE-04, OUT-05
// Esperado: REJECT codegen IRGEN-MISSING-RETURN
function incompleta(b: boolean): integer {
  if (b) { return 1; }
}
let resultado: integer = incompleta(false);

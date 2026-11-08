// IDs: PIPE-01, IDE-04, CLI-02, E2E-01
// Esperado: REJECT semantic
// Errores de tipos: el análisis semántico rechaza el programa, no existe TAC ni
// ensamblador, y ningún consumidor conserva el ASM de una compilación anterior.
let total: integer = "diez";
let activo: boolean = 1;
print(total + activo);

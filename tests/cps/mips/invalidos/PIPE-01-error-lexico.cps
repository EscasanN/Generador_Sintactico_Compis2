// IDs: PIPE-01
// Esperado: REJECT syntax
// Un carácter que ningún token reconoce detiene la compilación en el frontend:
// el backend MIPS nunca se invoca y no hay ensamblador parcial.
let precio: integer = 10 # 2;

// IDs: EXC-02
// Esperado: RUNTIME INDEX_OUT_OF_RANGE
// El manejador se retira antes de ejecutar su catch: un error dentro del catch
// no vuelve a entrar en él y, sin manejador exterior, termina el programa.
let cero: integer = 0;
let lista: integer[] = [1];
try {
  print(1 / cero);
} catch (e) {
  print(e);
  print(lista[3]);
}
print("nunca");

// IDs: CLS-02, CLS-04, CLS-05, FUN-07, FUN-08, RUN-03
// Esperado: ACCEPT
function cero(): integer { return 0; }
let guardado = cero;
function instalar() {
  let base: integer = 7;
  class Contador {
    let inicial: integer = base;
    function siguiente(): integer {
      function actualizar() { inicial = inicial + base; }
      actualizar();
      return inicial;
    }
  }
  let contador = new Contador();
  guardado = contador.siguiente;
}
instalar();
print(guardado());
print(guardado());

// CTL-04: el parametro de catch es string y solo existe en su manejador.
try {
  print("operacion");
} catch (error) {
  let mensaje: string = "error: " + error;
  print(mensaje);
}

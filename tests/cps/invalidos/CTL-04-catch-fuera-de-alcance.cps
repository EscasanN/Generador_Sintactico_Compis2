// CTL-04 invalido: error solo existe dentro del bloque catch.
try {
  print("operacion");
} catch (error) {
  print(error);
}

print(error);

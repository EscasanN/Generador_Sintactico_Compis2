// IDs: CTL-06
// Esperado: ACCEPT
// En Compiscript el discriminante de switch es boolean. Se evalúa una sola
// vez; cada case se compara contra él y salta a su etiqueta, con caída entre
// casos y un default final.
let opcion: integer = 2;
let resultado: string = "";
switch (opcion + 1 > 2) {
  case opcion == 1:
    resultado = "uno";
  case opcion % 2 == 0:
    resultado = "par";
  default:
    resultado = resultado + "!";
}

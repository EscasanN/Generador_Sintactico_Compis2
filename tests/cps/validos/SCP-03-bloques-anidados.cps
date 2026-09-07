// SCP-03: los bloques anidados acceden a sus ancestros.
let raiz: integer = 7;
{
  let nivelUno: integer = raiz;
  {
    let nivelDos: integer = nivelUno + raiz;
    print(nivelDos);
  }
}

// SCP-02: un bloque hijo puede ocultar un nombre del padre.
let nombre: string = "global";
{
  let nombre: string = "local";
  print(nombre);
}
print(nombre);

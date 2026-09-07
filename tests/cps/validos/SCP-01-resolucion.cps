// SCP-01: se resuelve el nombre mas cercano y tambien el global.
let valor: string = "global";
{
  let valor: integer = 2;
  let local: integer = valor;
}
let global: string = valor;

// IDs: STR-01, PIPE-01
// Esperado: ACCEPT
// Cadenas: concatenación en memoria nueva, igualdad por contenido entre
// direcciones distintas, orden por bytes UTF-8 sin signo, cadena vacía,
// Unicode impreso con longitud explícita y null distinto de "".
let a: string = "Compi";
let b: string = "script";
let c: string = a + b;
print(c);
let d: string = "Compi" + "script";
print(c == d);
print(c != d);
print("abc" < "abd");
print("abc" < "ab");
print("ab" <= "ab");
print("b" > "a");
print("a" >= "b");
print("Z" < "a");
print("é" > "z");
let vacia: string = "";
print(vacia == "");
print(vacia + "x" + vacia);
print(vacia);
print("canción, ñandú y €");
let sinValor: string;
print(sinValor);
print(sinValor == vacia);
print(sinValor == sinValor);
let saludo: string = "hola";
saludo = saludo + " " + "mundo";
print(saludo);

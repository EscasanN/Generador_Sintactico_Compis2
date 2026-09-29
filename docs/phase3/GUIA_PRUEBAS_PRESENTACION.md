# Guía de pruebas y presentación — Proyecto 2

Esta guía permite verificar de principio a fin el analizador sintáctico y
semántico de Compiscript conforme al
[enunciado del proyecto](../../Generador_de_Analizadores_Semánticos.pdf).
La explicación de arquitectura, flujo interno, perfiles y posibles preguntas
del profesor está reunida en la
[guía completa de la entrega y defensa](GUIA_COMPLETA_ENTREGA_Y_DEFENSA.md).

## 1. Preparar el proyecto

Desde PowerShell, en la raíz del repositorio:

```powershell
git switch fix/fase3-final-compliance

python -m pip install -r requirements.txt

java -version
dot -V
python -c "import antlr4, PyQt6; print('Dependencias correctas')"
```

El entorno validado durante la revisión utiliza:

- Python 3.14;
- Java 21;
- Graphviz 15;
- ANTLR runtime 4.13.2;
- PyQt6.

Antes de la presentación conviene ejecutar ANTLR al menos una vez con acceso a
Internet. De esa forma el JAR y los parsers generados quedan disponibles en la
caché ignorada bajo `output/antlr/`.

## 2. Ejecutar las pruebas automatizadas

### Núcleo semántico

```powershell
python -m pytest tests/semantic/test_diagnostics.py -q
python -m pytest tests/semantic/test_types.py -q
python -m pytest tests/semantic/test_expressions.py -q
```

Resultados esperados:

```text
5 passed
40 passed
67 passed
```

### Integración y regresiones

```powershell
python -m pytest tests/antlr_mode -q
python -m pytest tests/semantic -q
python -m pytest tests/gui -q
python -m pytest tests -q
```

Resultados esperados en la revisión del 7 de septiembre de 2026:

```text
ANTLR:      12 passed
Semántica: 362 passed
GUI:        11 passed
Total:     388 passed
```

Para aislar un requisito concreto de la matriz:

```powershell
python -m pytest tests/semantic/test_end_to_end.py -q -k "typ_01"
python -m pytest tests/semantic/test_end_to_end.py -q -k "fun_04"
python -m pytest tests/semantic/test_end_to_end.py -q -k "cls_01"
python -m pytest tests/gui/test_cps_workflow.py -q -k "ide_04"
```

## 3. Abrir y configurar el IDE

Ejecutar:

```powershell
python -m src.main
```

En la interfaz:

1. Seleccionar **ANTLR (.g4)** en `Mode`.
2. Presionar **Open G4**.
3. Abrir `src/compiscript/grammar/Compiscript.g4`.
4. Confirmar que la regla inicial sea `program`.
5. Presionar **Load Profile**.
6. Abrir `semantic_profiles/compiscript.semantic.json`.
7. Usar **File → New .cps** o **Open Input**.
8. Escribir o cargar el programa.
9. Presionar **Analyze** o `Ctrl+R`.

El IDE debe presentar:

- `Results`: aceptación o rechazo del programa;
- `Parse Tree`: imagen Graphviz y árbol navegable;
- `Semantics`: diagnósticos con severidad, categoría, línea y columna;
- tabla de símbolos con entornos globales, de función, clase y bloque;
- tokens producidos por ANTLR.

El análisis semántico usa el contenido actual del editor, aunque todavía no se
haya guardado.

## 4. Demostración integral válida

Abrir directamente [`tests/cps/demostracion-valida.cps`](../../tests/cps/demostracion-valida.cps).
Este archivo es la única fuente de verdad para la demostración y también se
compila automáticamente desde `tests/semantic/test_cps_programs.py`.

Resultado esperado:

```text
Sintaxis: ACCEPT
Semántica: ACCEPT
Diagnósticos semánticos: ninguno
```

Este programa demuestra:

- clases, campos, métodos, constructor, `this` y herencia;
- acceso a miembros heredados y asignación de una subclase a su ancestro;
- llamadas adelantadas y recursión mutua entre funciones globales;
- referencias de clase anulables;
- módulo `%` y concatenación `string + string`;
- arreglos y un iterador `foreach` correctamente tipado;
- parámetro de `catch` limitado a su entorno;
- condición booleana de `switch`;
- tabla de símbolos con entornos globales, de clase, función y bloque.

## 5. Demostración con errores acumulados

Abrir directamente
[`tests/cps/demostracion-invalida.cps`](../../tests/cps/demostracion-invalida.cps).
La prueba automática exige que este único archivo alcance las seis familias de
diagnóstico principales.

Resultado esperado:

```text
Sintaxis: ACCEPT
Semántica: REJECT
```

Deben acumularse diagnósticos de estas categorías:

| Categoría | Error provocado |
|---|---|
| `type` | Asignar `string` a `integer` |
| `scope` | Usar `ausente` sin declararlo |
| `control_flow` | Ejecutar `break` fuera de un bucle |
| `function` | Retorno incorrecto y cantidad incorrecta de argumentos |
| `array` | Construir una lista heterogénea |
| `class` | Acceder al miembro inexistente `noExiste` |

El análisis no debe detenerse después del primer error.

## 6. Casos pequeños por requisito

Los archivos canónicos para estos casos están en
[`tests/cps/validos`](../../tests/cps/validos) y
[`tests/cps/invalidos`](../../tests/cps/invalidos). Los fragmentos siguientes
sirven únicamente como explicación rápida; para la defensa se deben abrir los
archivos versionados, que son los que ejecuta la suite automática.

### Sistema de tipos

Aritmética válida y fallida (`TYP-01`):

```cps
let valid: float = 1.5 * 2;
let invalid: integer = true + 1;
```

Lógica válida y fallida (`TYP-02`):

```cps
let valid: boolean = true && !false;
let invalid: boolean = 1 && true;
```

Comparaciones (`TYP-03`):

```cps
let valid: boolean = 1 < 2.5;
let invalid: boolean = 1 == "one";
```

Asignaciones (`TYP-04`):

```cps
let value: integer = 1;
value = 2;
value = "text";
```

Constantes (`TYP-05`):

```cps
const LIMIT: integer = 10;
```

La siguiente declaración debe rechazarse sintácticamente porque la gramática
obliga a inicializar una constante:

```cps
const LIMIT: integer;
```

### Ámbitos

Shadowing válido (`SCP-01` a `SCP-03`):

```cps
let value: integer = 1;

{
  let value: integer = 2;
  print(value);
}

print(value);
```

Variable no declarada:

```cps
print(notDeclared);
```

Redeclaración inválida:

```cps
let value: integer = 1;
let value: integer = 2;
```

### Funciones y procedimientos

Llamada correcta (`FUN-01`):

```cps
function add(a: integer, b: integer): integer {
  return a + b;
}

let result: integer = add(1, 2);
```

Cantidad de argumentos incorrecta:

```cps
function add(a: integer, b: integer): integer {
  return a + b;
}

let result = add(1);
```

Retorno incorrecto (`FUN-02`):

```cps
function invalid(): integer {
  return "text";
}
```

La demostración integral cubre además recursión, funciones anidadas y closures
(`FUN-03` y `FUN-04`). Las pruebas automatizadas cubren la redeclaración de
funciones (`FUN-05`).

### Control de flujo

Las condiciones de `if`, `while`, `do-while`, `for` y `switch` deben ser
booleanas (`CTL-01`). El PDF se sigue literalmente también para `switch`.

`break` y `continue` fuera de un bucle son inválidos (`CTL-02`):

```cps
break;
continue;
```

`return` fuera de una función es inválido (`CTL-03`):

```cps
return 1;
```

### Clases y objetos

Caso válido (`CLS-01` a `CLS-03`):

```cps
class Point {
  let x: integer;

  function constructor(value: integer) {
    this.x = value;
  }

  function getX(): integer {
    return this.x;
  }
}

let point = new Point(10);
let result: integer = point.getX();
```

Miembro inexistente:

```cps
class Empty {
  function constructor() {
  }
}

let instance = new Empty();
print(instance.missing);
```

Uso inválido de `this`:

```cps
let value = this;
```

### Listas

Lista e índice válidos (`LST-01` y `LST-02`):

```cps
let values: integer[] = [1, 2, 3];
let first: integer = values[0];
```

Lista heterogénea:

```cps
let values = [1, "two"];
```

Índice inválido:

```cps
let values: integer[] = [1, 2, 3];
let first = values[1.5];
```

También deben rechazarse índices `string` y `boolean`.

### Reglas generales

Código muerto (`GEN-01`):

```cps
function example(): integer {
  return 1;
  print(2);
}
```

El programa permanece aceptado porque el código muerto se reporta como
`WARNING`, pero debe aparecer un diagnóstico `general` de instrucción
inalcanzable.

Las pruebas de expresiones cubren el rechazo de operaciones como multiplicar
funciones, clases o arreglos (`GEN-02`). Las pruebas de declaraciones cubren
variables y parámetros duplicados (`GEN-03`).

## 7. Revisar la tabla de símbolos

Con la demostración integral válida, abrir `Semantics` y verificar:

- entorno `global`: clases `BaseCounter` y `Counter`, funciones `isEven` e
  `isOdd`, y las variables de la demostración;
- entornos de función: parámetros y variables locales de métodos y funciones;
- entornos de clase: campo `value` y métodos de ambas clases;
- entornos de bloque: cuerpos de funciones, `foreach`, `try` y `catch`.

Los entornos cerrados deben permanecer visibles al terminar el análisis.

## 8. Verificar las regresiones YALex y YAPar

```powershell
$cases = @(
  "01_arithmetic_id",
  "02_arithmetic_extended",
  "03_arithmetic_numbers",
  "04_assignments",
  "05_classes_functions",
  "06_rejection_examples"
)

foreach ($case in $cases) {
  python src/main.py --cli `
    "tests/cases/$case/lexer.yal" `
    "tests/cases/$case/grammar.yapar" `
    "tests/cases/$case/input.txt"
}
```

Resultado esperado:

- los primeros cinco grupos suman 75 entradas `ACCEPT`;
- el último grupo contiene 8 entradas `REJECT`;
- SLR y LALR coinciden.

## 9. Flujo para el día de la presentación

### Si el profesor entrega un `.cps`

1. No reemplazar `Compiscript.g4`.
2. Cargar la gramática del repositorio.
3. Cargar `compiscript.semantic.json`.
4. Abrir el `.cps` proporcionado.
5. Confirmar que `Start` sea `program`.
6. Presionar **Analyze**.
7. Mostrar tokens y árbol sintáctico.
8. Mostrar diagnósticos o confirmar su ausencia.
9. Mostrar la tabla de símbolos por entorno.
10. Explicar que `ACCEPT` requiere sintaxis y semántica correctas.

### Si el profesor entrega una nueva gramática `.g4`

- El frontend puede cargarla y realizar análisis sintáctico dinámicamente.
- El perfil actual solo puede aplicarse si la gramática conserva las reglas y
  formas esperadas.
- Una gramática estructuralmente diferente necesita su propio perfil semántico.
- Se recomienda confirmar antes de la defensa si el archivo entregado será un
  programa `.cps` o una gramática `.g4`.

En el contexto del PDF, **compilar** significa generar Lexer y Parser, construir
el árbol y ejecutar el análisis semántico. El proyecto no ejecuta sentencias
`print` ni genera bytecode o código máquina.

## 10. Límites conocidos

El mínimo explícito del PDF y las extensiones de la gramática están cubiertos:

- `string + string` produce `string`; las mezclas con números se rechazan;
- `%` usa las reglas numéricas de los demás operadores aritméticos;
- la herencia resuelve miembros, superclases posteriores y asignación a un
  ancestro;
- `foreach` exige un arreglo y declara el iterador con el tipo del elemento;
- el parámetro de `catch` es `string` y no escapa de su manejador;
- una clase sin constructor explícito acepta `new Tipo()` de aridad cero;
- `switch` exige una expresión booleana conforme a la redacción del PDF.

Los límites que sí permanecen son:

- una gramática `.g4` estructuralmente distinta necesita su propio perfil
  semántico;
- las funciones anidadas se declaran secuencialmente y no tienen un prepass de
  recursión mutua propio;
- debe confirmarse externamente que la gramática incluida coincide con la
  versión oficial definitiva del profesor.

## 11. Lista de control previa a la defensa

- [ ] Los cambios de `fix/fase3-final-compliance` están revisados y versionados.
- [ ] La rama que se presentará está disponible en GitHub.
- [ ] `python -m pytest tests -q` termina con 388 pruebas aprobadas.
- [ ] Java y Graphviz responden desde una terminal nueva.
- [ ] ANTLR ya está disponible en caché.
- [ ] La demostración válida produce `ACCEPT`.
- [ ] La demostración negativa muestra las seis categorías de diagnóstico.
- [ ] El árbol visual se abre correctamente.
- [ ] Los cuatro tipos de entorno aparecen en la tabla de símbolos.
- [ ] El equipo conserva la evidencia de autorización para cuatro integrantes.
- [ ] Se confirmó qué tipo de archivo entregará el profesor.

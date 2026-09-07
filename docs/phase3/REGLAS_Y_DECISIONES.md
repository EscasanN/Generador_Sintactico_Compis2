# Reglas y decisiones — Compiscript

Este documento evita que ejemplos internos contradigan el enunciado. La gramática
actual es un ejemplo base, no la versión final oficial. Cualquier diferencia con
otra gramática o corrección del profesor debe registrarse aquí con fecha. El
motor carga gramáticas en tiempo de ejecución y no se modifica por cada archivo.

## Decisiones confirmadas

| Tema | Decisión |
|---|---|
| Tamaño del equipo | Cuatro integrantes, autorizado por el profesor. |
| Entornos | Crear scopes globales, de función, clase y bloque. |
| Redeclaración | Prohibida en el mismo scope. |
| Resolución | Buscar desde el scope actual hacia sus ancestros. |
| Constantes | Deben inicializarse al declararse. |
| Argumentos | Validar cantidad y compatibilidad posicional. |
| Retorno | Validar ubicación y compatibilidad con el tipo declarado. |
| Listas | Validar homogeneidad e índices de tipo entero. |
| Clases | Validar atributos, métodos, constructores y `this`. |
| Reportes | Incluir categoría, mensaje, línea y columna. |
| Pruebas | Incluir al menos un caso exitoso y uno fallido por regla. |
| Gramática como entrada | Seleccionar otro `.g4` no requiere cambios en Python. |
| Entrada evaluada | El IDE crea, abre, edita, guarda y compila archivos `.cps`. |
| Recorrido | La integración semántica usa Listener/Visitor de ANTLR sobre el árbol nativo. |
| Árbol | Se presenta visualmente mediante nodos y aristas. |
| Aceptación | Requiere cero errores léxicos, sintácticos y semánticos. |
| Perfil JSON | Es configuración declarativa interna; no reemplaza el Listener/Visitor. |
| Modos previos | YALex y YAPar se conservan completos. |
| Generados | Se almacenan solo en `output/antlr/` y no se versionan. |
| Orden de trabajo | Daniel, Nadissa, Dulce y Nelson trabajan en ese orden. |
| Cierre de bloques | Cada responsable corrige y termina su bloque antes de integrarlo. |
| Contratos | Una API aceptada no se cambia en un bloque posterior. |
| Dependencias | Se puede usar un bloque anterior; nunca se deja trabajo para que su autor regrese. |

## Lectura literal del enunciado oficial

Salvo corrección escrita posterior del profesor, se implementan estas reglas tal
como aparecen en el PDF:

- Las condiciones de `if`, `while`, `do-while`, `for` y `switch` deben ser booleanas.
- `break` y `continue` solo son válidos dentro de bucles.
- Los operandos aritméticos deben ser `integer` o `float`.

Por tanto, `switch` no usa por defecto la semántica convencional de un
discriminante arbitrario y `break` dentro de `switch` no se permite si no existe
también un bucle envolvente. Cualquier corrección del profesor se registra antes
de cambiar el perfil y las pruebas.

## Preguntas pendientes y bloque responsable

Estas preguntas no requieren que los cuatro integrantes trabajen al mismo
tiempo. Cada una se resuelve y documenta dentro del bloque indicado, antes de
cerrarlo:

- Daniel: compatibilidad de tipos, literales y `null`;
- Nadissa: declaraciones, funciones, control, scopes y clases;
- Dulce: diferencias sintácticas detectables desde la gramática;
- Nelson: correspondencia final entre la gramática de entrega y su perfil.

Si una respuesta del profesor cambia una decisión antes de cerrar el bloque
responsable, ese bloque incorpora la corrección. Después de aceptarse una
puerta, los bloques posteriores adaptan sus propios archivos sin pedir que un
integrante anterior regrese.

| Pregunta | Riesgo si no se resuelve |
|---|---|
| ¿La gramática final incluirá literales `float`? | El enunciado exige operaciones con `float`, pero la gramática base no contiene un literal decimal. |
| ¿La concatenación `string + string` está permitida? | Los ejemplos informales suelen usarla, pero la regla aritmética menciona solamente números. |
| ¿La falta de inicialización de `const` debe ser error sintáctico o semántico? | Si la gramática exige `= expression`, el árbol nunca contendrá una constante incompleta. |
| ¿Se exige herencia o es una mejora opcional? | Puede consumir tiempo sin aportar al mínimo evaluado. |
| ¿La gramática permite `else if` directamente? | No debe incluirse como fixture válido si solo acepta `else` seguido de bloque. |
| ¿Existe sintaxis `new Tipo[tamaño]`? | No debe asumirse para arreglos si la gramática solo permite literales de lista. |
| ¿Se permite omitir el tipo de un parámetro? | El equipo debe acordar si se infiere o se representa como tipo desconocido. |
| ¿Se permite declarar una variable sin tipo y sin inicializador? | Sin ninguna de las dos fuentes no hay información suficiente para determinar su tipo. |
| ¿Una función sin anotación de retorno es `void` o infiere el tipo? | Cambia la validación de cada sentencia `return`. |
| ¿`null` puede asignarse a clases y arreglos? | Se necesita una única regla de compatibilidad para todos los integrantes. |
| ¿El cuerpo de un `if` requiere llaves obligatoriamente? | La gramática exige bloques, pero algunos ejemplos pueden mostrar sentencias individuales. |

El perfil JSON es una decisión interna de arquitectura: asocia reglas con
acciones seguras, mientras un Listener/Visitor de ANTLR realiza el recorrido
exigido. Si el profesor entrega acciones o convenciones adicionales, se traducen
al mismo registro sin ejecutar código arbitrario desde el perfil.

## Reglas para crear fixtures

- Cada fixture debe parsearse correctamente antes de usarse para probar semántica, salvo que sea una prueba sintáctica negativa.
- No se inventarán palabras clave ni construcciones ausentes de la gramática
  seleccionada y el enunciado.
- Un caso semántico negativo debe tener sintaxis válida; de lo contrario solo demuestra un error del parser.
- Cada fixture indicará qué regla valida y qué diagnósticos espera.
- Cada fixture registra la gramática y regla inicial usadas.
- Cuando se entregue otra gramática se carga desde el IDE y se ejecuta nuevamente
  la matriz; no se modifica el motor.

## Matriz inicial de cobertura

| Dominio | Casos mínimos |
|---|---|
| Tipos | aritmética, lógica, comparación, asignación y constante |
| Ámbitos | no declarado, redeclaración, bloque anidado y shadowing |
| Funciones | argumentos, retornos, recursión, anidamiento y closure |
| Control | condiciones, `break`, `continue`, `return` y código muerto |
| Clases | atributo, método, constructor y `this` |
| Listas | homogeneidad, índice y asignación de elemento |
| Integración | programa válido completo y programa con errores de varias categorías |

Esta tabla es solo un resumen. La fuente de verdad para casos positivos,
negativos, responsables y evidencia es
[`MATRIZ_CUMPLIMIENTO.md`](MATRIZ_CUMPLIMIENTO.md).

## 2026-09-05 — Bloque 4 (Nelson): reestructuración de `Compiscript.g4`

Al construir `semantic_profiles/compiscript.semantic.json` contra la gramática
de ejemplo disponible con el JAR real de ANTLR, se confirmó empíricamente que el
selector de perfiles (`src/semantic/profile.py`, congelado en el bloque 2) solo
puede leer un hijo por índice fijo, un terminal directo por tipo de token, el
texto concatenado del nodo actual, o todos los hijos a la vez. No existe forma
de aplanar una lista de aridad variable, de saber qué alternativa opcional se
usó sin etiquetarla, ni de encadenar el resultado de una acción hacia otra
acción del mismo nodo. La gramática de ejemplo original combinaba, en varias
reglas, dos o más partes opcionales independientes en una sola alternativa sin
etiquetar (`variableDeclaration`, `functionDeclaration`, `forStatement`, la
lista de argumentos/parámetros como `X (',' X)*`, etc.), lo cual produce un
árbol de aridad variable que el sistema de selectores no puede consumir de
forma segura (en el mejor caso, `null` en camino a una acción que no lo
tolera; en el peor, una excepción de Python sin diagnóstico).

Se decide reestructurar `Compiscript.g4` con estas técnicas, ya usadas en
`MiniCalc.g4` y explícitamente permitidas porque la gramática es "un ejemplo
base, no la versión final" (ver encabezado de este documento):

- Toda alternativa que combinaba partes opcionales independientes se separó en
  alternativas etiquetadas de aridad fija (una por combinación). Afecta a
  `variableDeclaration`, `constantDeclaration`, `assignment`, `ifStatement`,
  `forStatement`, `returnStatement`, `functionDeclaration`, `parameter`,
  `classDeclaration`.
- Las cadenas binarias (`logicalOrExpr` … `multiplicativeExpr`), el postfijo
  (`leftHandSide`, antes `primaryAtom (suffixOp)*`) y las listas separadas por
  coma (`argumentList`, `elementList`) se reescribieron en forma recursiva a la
  izquierda con una alternativa por paso, para que el valor acumulado quede
  siempre en un índice fijo (posición 0), igual que en `MiniCalc.g4`.
- `classMember` ya no reutiliza `functionDeclaration`/`variableDeclaration`/
  `constantDeclaration`; ahora usa reglas dedicadas (`classMethod`,
  `classField`, `classConstant`) porque el enlace del perfil se hace por
  nombre de regla sin importar el ancestro, y las acciones para miembro de
  clase (`class.field`, `class.method`) son distintas de las de nivel
  superior (`declare.variable`, `function.declare`).
- El léxico `Literal` (que combinaba `IntegerLiteral` y `StringLiteral` en un
  solo tipo de token) se separó en dos tokens independientes, porque el perfil
  necesita el tipo de token para decidir `kind="integer"` vs `kind="string"` en
  `expression.literal` y un token combinado pierde esa distinción.

Ninguno de estos cambios modifica el lenguaje aceptado; solo cambia la forma
del árbol de derivación. Se verificó con `python -m pytest tests/antlr_mode
tests/semantic/test_generic_grammar.py -q` (19 passed) y la suite completa (195
passed) antes y después de cada cambio, y con volcados de árbol ad hoc contra
el JAR real para confirmar la aridad exacta de cada alternativa.

### Composiciones genéricas incorporadas al registro público

El selector declarativo no puede aplanar por sí solo listas recursivas ni
encadenar el resultado de dos acciones hermanas. Las composiciones necesarias
se ubican en `src/semantic/actions/composition.py` y se registran mediante
`register_builtin_actions`. Incluyen acumulación de listas, extracción de texto
de subárbol, arreglos, asignaciones, firmas obtenidas del árbol y recorte de
terminales para detección de código muerto.

Estas acciones no contienen nombres de reglas ni tokens de Compiscript. Cada
identificador de gramática requerido se pasa como argumento escalar desde
`semantic_profiles/compiscript.semantic.json`. La GUI no registra ni ejecuta
lógica semántica propia y usa el adaptador público
`analyze_semantics_with_g4`, igual que MiniCalc y cualquier otro perfil.

Para que el orden textual no altere la validez de una clase, la acción
`class.predeclare_members` publica firmas de métodos y tipos declarados de
campos al entrar al entorno de clase. Las acciones normales recorren después
cada declaración, validan inicializadores y detectan duplicados.

### Respuestas a preguntas pendientes (a partir de esta implementación)

| Pregunta | Respuesta adoptada |
|---|---|
| ¿La gramática final incluirá literales `float`? | La gramática de entrega acepta literales decimales y exponenciales; el perfil los convierte con `expression.literal`. La procedencia oficial de la gramática aún requiere confirmación externa. |
| ¿La concatenación `string + string` está permitida? | Sí para dos operandos `string`; mezclar cadena y número se rechaza. |
| ¿Se exige herencia? | Se implementa preventivamente: vínculo de superclase, asignación a ancestros y búsqueda heredada de miembros. |
| ¿Se permite omitir el tipo de un parámetro? | Sí, se representa como tipo `UNKNOWN` (`resolve_type(None)`). |
| ¿Una función sin anotación de retorno es `void`? | Sí, `return_type` por defecto es `VOID`. |
| ¿El cuerpo de un `if`/`while`/`for` requiere llaves? | Sí, la gramática solo acepta `block` (con llaves) como cuerpo. |
| ¿`new Tipo()` requiere un método `constructor` explícito? | No para cero argumentos: toda clase sin constructor explícito dispone de uno implícito de aridad cero. |

### Limitaciones documentadas

- `PropertyAssignExpr` (alternativa de `assignmentExpr`) queda sin enlazar: es
  código muerto confirmado — cualquier entrada que la alcanzaría ya es
  consumida antes por la alternativa `PropertyAssignment` de la sentencia
  `assignment`, que aparece primero en `statement`.
- Las funciones globales se predeclaran; las funciones anidadas conservan
  declaración secuencial y autorrecursión, pero no un prepass mutuo propio.
- Una `.g4` distinta puede analizarse sintácticamente de inmediato, pero su
  semántica requiere un perfil compatible con sus reglas y forma de árbol.

## Alcance no mínimo

`foreach`, `try/catch`, herencia y `new` aparecen en la especificación de
ejemplo, pero no están enumerados como reglas semánticas mínimas en el PDF. Se
implementaron después de completar la matriz oficial para endurecer la entrega.

## 2026-09-06 — Endurecimiento para entradas externas

- `program.predeclare` registra primero clases, interfaces y funciones globales;
  soporta referencias adelantadas, recursión mutua y superclases posteriores.
- `ClassType.superclass` participa en compatibilidad y la búsqueda de miembros
  recorre la cadena de herencia con prioridad para el miembro más cercano.
- `null` puede asignarse a clases y arreglos, y participa en el tipo común de
  expresiones de referencia.
- `%` usa las mismas reglas numéricas que los demás operadores aritméticos y
  `string + string` produce `string`.
- Una clase sin constructor explícito acepta `new Tipo()` pero rechaza
  argumentos.
- La fase de perfil `after_child` permite declarar el iterador de `foreach` con
  el tipo del arreglo antes del bloque. Un iterable no arreglo se rechaza.
- El parámetro de `catch` se declara como `string` en un scope que no escapa del
  manejador.
- `python -m src.main --cps` ejecuta el flujo completo incluido. Con una `.g4`
  externa sin perfil compatible, informa y ejecuta solamente sintaxis.
- Los perfiles incluidos guardan nombre y SHA-256 normalizado de la gramática;
  el adaptador rechaza una sustitución distinta antes de ejecutar acciones.

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
oficial de ejemplo con el JAR real de ANTLR, se confirmó empíricamente que el
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

### Extensiones de acciones fuera del motor congelado

El conjunto de acciones publicado (bloques 1 y 2) no incluye una acción
genérica para "construir una tupla limpia a partir de una lista separada por
comas" ni para "componer dos acciones ya publicadas sobre el mismo nodo". Se
confirmó que ningún selector ni acción existente cubre, de forma segura, listas
de llamada/arreglo de aridad arbitraria ni la asignación de nivel superior
(`x = expr;`, `x.y = expr;`, que no pasan por `leftHandSide`). En vez de pedir
que un bloque anterior regrese, se añadió `src/gui/semantic_bridge.py` (archivo
propio de Nelson, no modifica ningún archivo de Daniel, Nadissa o Dulce) con
un puñado de acciones adicionales, neutras respecto a Compiscript, registradas
bajo el prefijo `x.` para que sean auditables a simple vista en el perfil:
acumulación de listas (`x.list_start`/`x.list_append`), extracción de texto de
subárbol (`x.text`), construcción de arreglo con valor por defecto seguro
(`x.array`), composición resolución+asignación (`x.assign_identifier`/
`x.assign_member`), declaración de función/método a partir del árbol crudo de
parámetros (`x.declare_function`/`x.declare_method`, ver docstring del módulo
para la razón de leer el árbol sintáctico en vez de un selector) y recorte de
terminales estructurales antes de la detección de código muerto
(`x.sequence`). Cada función solo compone o delega en las funciones reales ya
publicadas (`ExpressionActions`, `resolve_identifier`, `access_member`,
`declare_function`, `declare_method`, `validate_sequence`); ninguna reimplementa
su lógica. `analyze_semantics_with_extensions` (mismo módulo) reutiliza sin
cambios `analyze_with_g4`, `load_profile`, `validate_profile`,
`SemanticTreeListener` y `SemanticEvaluator(registry=...)` — este último ya
aceptaba un registro personalizado como punto de extensión documentado — para
inyectar el registro extendido; el IDE y las pruebas de Compiscript deben usar
esta función en vez de `analyze_semantics_with_g4` directamente, porque el
perfil de Compiscript referencia acciones `x.*` que el registro por defecto no
tiene.

### Respuestas a preguntas pendientes (a partir de esta implementación)

| Pregunta | Respuesta adoptada |
|---|---|
| ¿La concatenación `string + string` está permitida? | No: `ExpressionActions.binary` (congelado) solo acepta operandos numéricos para `+`. Se documenta como limitación conocida. |
| ¿Se exige herencia? | No. `declare_class`/`construct` (congelados) no aceptan superclase. `class X : Y` se acepta sintácticamente pero el vínculo de herencia se ignora semánticamente; queda documentado. |
| ¿Se permite omitir el tipo de un parámetro? | Sí, se representa como tipo `UNKNOWN` (`resolve_type(None)`). |
| ¿Una función sin anotación de retorno es `void`? | Sí, `return_type` por defecto es `VOID`. |
| ¿El cuerpo de un `if`/`while`/`for` requiere llaves? | Sí, la gramática solo acepta `block` (con llaves) como cuerpo. |
| ¿`new Tipo()` requiere un método `constructor` explícito? | Sí: `construct` (congelado) exige un miembro llamado literalmente `constructor`; una clase sin ese método no puede instanciarse con `new`. |

### Limitaciones documentadas (no mínimas o fuera del alcance de las acciones congeladas)

- `foreach`/`try-catch`: implementados de forma mínima (no bloquean, no
  crashean) pero sin inferencia de tipo de elemento (`foreach`) ni declaración
  del parámetro de `catch` dentro de su propio bloque — ambas son
  explícitamente "no mínimas" según `MATRIZ_CUMPLIMIENTO.md`.
- Inicializador de un campo de clase (`let x: integer = ...;` dentro de una
  clase): `declare_field` (congelado) no tiene parámetro `initializer`, por lo
  que el valor se visita y valida por sí mismo pero no se compara contra el
  tipo declarado del campo.
- `PropertyAssignExpr` (alternativa de `assignmentExpr`) queda sin enlazar: es
  código muerto confirmado — cualquier entrada que la alcanzaría ya es
  consumida antes por la alternativa `PropertyAssignment` de la sentencia
  `assignment`, que aparece primero en `statement`.
- El operador `%` se enlaza a `expression.binary` aunque esa acción no lo
  soporta; produce un diagnóstico `GENERAL` de "operador no soportado" en vez
  de aritmética real. No está en la matriz mínima.

## Alcance no mínimo

`foreach`, `try/catch`, herencia y `new` aparecen en la especificación de
ejemplo, pero no están enumerados como reglas semánticas mínimas en el PDF. Se
implementan después de completar la matriz oficial, salvo que la gramática final
o una instrucción del profesor los vuelva obligatorios.

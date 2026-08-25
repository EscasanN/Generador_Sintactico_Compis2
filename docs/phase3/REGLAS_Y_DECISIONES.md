# Reglas y decisiones — Compiscript

Este documento evita que ejemplos internos contradigan el enunciado o la gramática oficial. Cualquier corrección del profesor debe registrarse aquí con fecha.

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

## Política provisional ante contradicciones

Hasta recibir una corrección escrita, se implementará la lectura literal del enunciado de evaluación:

- Las condiciones de `if`, `while`, `do-while`, `for` y `switch` deben ser booleanas.
- `break` y `continue` solo son válidos dentro de bucles.
- Los operandos aritméticos deben ser `integer` o `float`.

Si el profesor confirma semántica convencional para `switch` o permite `break` dentro de este, se actualizarán primero este documento y sus pruebas.

## Preguntas que deben resolverse en la Fase 0

| Pregunta | Riesgo si no se resuelve |
|---|---|
| ¿La gramática oficial incluye literales `float`? | El enunciado exige operaciones con `float`, pero una gramática sin literal decimal no puede probarlas correctamente. |
| ¿La concatenación `string + string` está permitida? | Los ejemplos informales suelen usarla, pero la regla aritmética menciona solamente números. |
| ¿La falta de inicialización de `const` debe ser error sintáctico o semántico? | Si la gramática exige `= expression`, el Visitor nunca verá una constante incompleta. |
| ¿`switch` realmente exige boolean o compara el discriminante con cada `case`? | Ambas interpretaciones producen pruebas y lógica diferentes. |
| ¿`break` es válido dentro de `switch`? | El enunciado literal lo restringe a bucles. |
| ¿Se exige herencia o es una mejora opcional? | Puede consumir tiempo sin aportar al mínimo evaluado. |
| ¿La gramática permite `else if` directamente? | No debe incluirse como fixture válido si solo acepta `else` seguido de bloque. |
| ¿Existe sintaxis `new Tipo[tamaño]`? | No debe asumirse para arreglos si la gramática solo permite literales de lista. |

## Reglas para crear fixtures

- Cada fixture debe parsearse correctamente antes de usarse para probar semántica, salvo que sea una prueba sintáctica negativa.
- No se inventarán palabras clave ni construcciones que no estén en la gramática oficial.
- Un caso semántico negativo debe tener sintaxis válida; de lo contrario solo demuestra un error del parser.
- Cada fixture indicará qué regla valida y qué diagnósticos espera.
- Los ejemplos removidos durante la limpieza no se restaurarán hasta validarlos contra el parser oficial.

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

# Matriz de cumplimiento — Proyecto 2

Este documento convierte el
[enunciado oficial](../../Generador_de_Analizadores_Semánticos.pdf) en criterios
verificables. Es la lista de control principal para decidir si el proyecto está
listo para evaluación.

## Alcance oficial

El producto evaluado es un IDE que permite escribir, cargar y compilar código
Compiscript `.cps`. El frontend se genera desde la gramática oficial ANTLR y un
Listener o Visitor recorre el árbol para ejecutar las reglas semánticas.

En este proyecto, **compilar** significa:

```text
Compiscript.g4
      │
      v
ANTLR genera Lexer + Parser Python
      │
      v
programa.cps → tokens → análisis sintáctico → árbol visual
                                              │
                                              v
                                Listener/Visitor semántico
                                              │
                          ┌───────────────────┴──────────────────┐
                          v                                      v
                 diagnósticos semánticos              tabla de símbolos
```

El enunciado no exige generación de código máquina, bytecode ni un ejecutable
nativo.

## Condición para aceptar un archivo `.cps`

Un programa se marca como **ACCEPT** solamente si:

1. el Lexer no reporta errores;
2. el Parser consume toda la entrada sin errores;
3. el perfil semántico es compatible con la gramática;
4. el recorrido semántico termina;
5. no existen diagnósticos semánticos de severidad `ERROR`.

Los warnings pueden mostrarse sin convertir el resultado en rechazo, salvo que
el profesor indique una política distinta.

## Trazabilidad de la evaluación

| Componente | Puntos | Evidencia obligatoria | Bloque principal |
|---|---:|---|---|
| IDE | 15 | Abrir, editar, guardar y compilar `.cps`; presentar árbol, errores y símbolos. | Nelson |
| Analizador sintáctico y semántico | 60 | Gramática oficial ANTLR, árbol visual, Listener/Visitor y pruebas positivas/negativas por regla. | Daniel, Nadissa y Dulce |
| Tabla de símbolos | 25 | Entornos global, función, clase y bloque preservados y visibles. | Nadissa y Nelson |

El proyecto debe funcionar el día de la presentación. Tener el código o las
pruebas sin una ejecución completa desde el IDE no satisface esa condición.

## Matriz mínima de pruebas semánticas

Cada fila exige al menos un caso exitoso y uno fallido. Los identificadores se
usan en nombres de fixtures, parametrizaciones o comentarios de prueba para que
la evidencia sea fácil de localizar.

### Sistema de tipos

| ID | Regla | Caso exitoso | Caso fallido | Responsable |
|---|---|---|---|---|
| `TYP-01` | Aritmética acepta `integer` o `float`. | `1 + 2`, `1.0 * 2` según la gramática oficial. | Multiplicar `string`, `boolean`, función o clase. | Daniel |
| `TYP-02` | Lógica exige `boolean`. | `true && !false`. | `1 && true`. | Daniel |
| `TYP-03` | Comparaciones usan tipos compatibles. | Dos números o valores compatibles. | Comparar tipos incompatibles. | Daniel |
| `TYP-04` | Asignación coincide con el tipo declarado. | Asignar valor compatible. | Asignar `string` a `integer`. | Daniel |
| `TYP-05` | `const` se inicializa al declararse. | Constante con inicializador compatible. | Constante sin inicializador. | Nadissa |
| `TYP-06` | Listas y estructuras conservan tipos válidos. | Lista homogénea. | Lista con elementos incompatibles. | Daniel |

Si la gramática oficial rechaza sintácticamente una constante sin inicializar,
`TYP-05` debe conservar una prueba unitaria con árbol manual para demostrar la
regla y una prueba sintáctica negativa para el archivo `.cps`.

### Manejo de ámbito

| ID | Regla | Caso exitoso | Caso fallido | Responsable |
|---|---|---|---|---|
| `SCP-01` | Resolución local y global. | Resolver el identificador más cercano. | Usar una variable no declarada. | Nadissa |
| `SCP-02` | No hay redeclaración en el mismo ámbito. | Shadowing en un ámbito hijo, si está permitido. | Declarar dos veces en el mismo scope. | Nadissa |
| `SCP-03` | Acceso correcto en bloques anidados. | Un bloque hijo accede a su ancestro. | Acceder desde un scope donde el nombre no es visible. | Nadissa |
| `SCP-04` | Cada función, clase y bloque crea entorno. | El resultado conserva los cuatro tipos de scope. | Reutilizar por error el scope padre. | Nadissa |

### Funciones y procedimientos

| ID | Regla | Caso exitoso | Caso fallido | Responsable |
|---|---|---|---|---|
| `FUN-01` | Cantidad y tipos de argumentos coinciden posicionalmente. | Llamada con firma correcta. | Cantidad o tipo incorrecto. | Nadissa |
| `FUN-02` | Retorno coincide con el tipo declarado. | Retorno compatible. | Retorno incompatible. | Nadissa |
| `FUN-03` | Se admiten funciones recursivas. | La función se resuelve dentro de su cuerpo. | Referencia recursiva sin símbolo de función. | Nadissa |
| `FUN-04` | Funciones anidadas y closures capturan el entorno de definición. | Función interna usa una variable externa visible. | Captura de un nombre inexistente o fuera de alcance. | Nadissa |
| `FUN-05` | No se redeclaran funciones con el mismo nombre. | Funciones con nombres distintos. | Dos funciones iguales en el mismo scope. | Nadissa |

### Control de flujo

| ID | Regla | Caso exitoso | Caso fallido | Responsable |
|---|---|---|---|---|
| `CTL-01` | `if`, `while`, `do-while`, `for` y `switch` exigen condición booleana. | Un caso booleano por construcción. | Un caso no booleano por construcción. | Nadissa |
| `CTL-02` | `break` y `continue` solo aparecen dentro de bucles. | Ambos dentro de un loop. | Ambos fuera de un loop. | Nadissa |
| `CTL-03` | `return` solo aparece dentro de una función. | Retorno dentro de función. | Retorno en scope global o de bloque sin función. | Nadissa |

La condición booleana de `switch` se implementa literalmente porque así lo
indica el enunciado, aunque otros lenguajes usen un discriminante no booleano.

### Clases y objetos

| ID | Regla | Caso exitoso | Caso fallido | Responsable |
|---|---|---|---|---|
| `CLS-01` | Los atributos y métodos accedidos con `.` existen. | Acceso a miembro declarado. | Acceso a miembro inexistente. | Nadissa |
| `CLS-02` | El constructor se invoca correctamente. | Cantidad y tipos correctos. | Constructor inexistente o argumentos incorrectos. | Nadissa |
| `CLS-03` | `this` solo se usa en el ámbito de clase permitido. | `this` dentro de método o constructor. | `this` fuera de una clase. | Nadissa |

### Listas y reglas generales

| ID | Regla | Caso exitoso | Caso fallido | Responsable |
|---|---|---|---|---|
| `LST-01` | Elementos de lista tienen tipo válido. | Lista homogénea. | Lista heterogénea incompatible. | Daniel |
| `LST-02` | Índices de lista son válidos. | Índice `integer`. | Índice `string`, `float` o `boolean`. | Daniel |
| `GEN-01` | Se detecta código muerto. | No hay instrucciones después de transferencia definitiva. | Instrucción después de `return` o `break`. | Nadissa |
| `GEN-02` | Las expresiones tienen sentido semántico. | Operandos compatibles. | Multiplicar una función u otro valor no numérico. | Daniel |
| `GEN-03` | Variables y parámetros duplicados se rechazan. | Nombres válidos según scope. | Duplicado en el mismo scope o firma. | Nadissa |

## Matriz de integración ANTLR

| ID | Requisito | Evidencia | Responsable |
|---|---|---|---|
| `ANT-01` | Generar Lexer y Parser desde la gramática oficial. | Parser generado en caché ignorada y análisis exitoso. | Dulce |
| `ANT-02` | Recorrer con Listener o Visitor de ANTLR. | Prueba que ejecuta `ParseTreeWalker` y `SemanticTreeListener`, o Visitor equivalente. | Dulce |
| `ANT-03` | Construir árbol sintáctico. | `ParseTreeNode` conserva regla, alternativa, token y ubicación. | Dulce |
| `ANT-04` | Mostrar representación visual. | Graphviz o vista jerárquica visual con nodos y aristas. | Dulce y Nelson |
| `ANT-05` | Consumir toda la entrada. | Se rechazan tokens sobrantes. | Dulce |
| `ANT-06` | Usar la gramática oficial final. | Dulce valida generación y recorrido antes de cerrar; Nelson repite la suite y ajusta únicamente el perfil. | Dulce → Nelson |

La prueba con MiniCalc demuestra generalidad, pero no reemplaza ninguna prueba
obligatoria de Compiscript.

Para conservar el flujo secuencial, Dulce no cierra su bloque hasta validar la
gramática oficial o recibir confirmación de que mantiene la forma ANTLR ya
soportada. Si el archivo oficial usa gramáticas separadas, imports, modos u otra
característica no cubierta, debe incorporarse en el bloque 3; no se difiere esa
modificación al bloque de Nelson.

## Matriz del IDE

| ID | Requisito | Evidencia | Responsable |
|---|---|---|---|
| `IDE-01` | Abrir un `.cps`. | Selector de archivo y contenido visible en el editor. | Nelson |
| `IDE-02` | Escribir y editar Compiscript. | Editor habilitado y cambios conservados durante el análisis. | Nelson |
| `IDE-03` | Guardar `.cps`. | Guardar y Guardar como sin cambiar la extensión accidentalmente. | Nelson |
| `IDE-04` | Compilar desde la interfaz. | Acción Compile/Analyze ejecuta sintaxis y semántica. | Nelson |
| `IDE-05` | Reportar errores con ubicación. | Categoría, mensaje, línea y columna visibles. | Nelson |
| `IDE-06` | Mostrar tabla por entorno. | Global, función, clase y bloque permanecen consultables. | Nelson |
| `IDE-07` | Mostrar árbol visual. | Vista navegable o imagen Graphviz legible. | Nelson |
| `IDE-08` | No bloquear Qt. | Generación, análisis y renderizado ocurren en worker. | Nelson |

## Entregables y evidencia

| Entregable | Condición verificable |
|---|---|
| Repositorio GitHub | Cada integrante tiene commits propios y claramente identificables. |
| Batería de pruebas | Todos los IDs anteriores tienen caso exitoso y fallido cuando aplica. |
| Arquitectura | `ARQUITECTURA.md` coincide con las dependencias reales. |
| Ejecución | README explica instalación, `.g4`, `.cps`, perfil y comandos de prueba. |
| IDE | La demostración completa funciona desde una sola ventana. |

Comandos de verificación esperados:

```bash
python -m pytest tests/antlr_mode -q
python -m pytest tests/semantic -q
python -m pytest tests/gui -q
python -m pytest -q
```

Si una carpeta todavía no existe durante un bloque temprano, se ejecutan las
pruebas disponibles. En la rama final deben existir y pasar las tres suites.

El PDF indica grupos de tres. El profesor autorizó explícitamente a este equipo
a trabajar con cuatro integrantes; debe conservarse la evidencia de esa
autorización. La excepción no elimina el requisito de commits individuales.

## Funcionalidades no mínimas

La especificación de ejemplo menciona `foreach`, `try/catch`, herencia y `new`,
pero el listado mínimo de reglas semánticas del PDF no las exige de forma
explícita. Se implementan solamente si aparecen en la gramática oficial, el
profesor las confirma o el equipo termina primero todos los criterios de esta
matriz.

## Cierre de evaluación

El proyecto está listo únicamente cuando:

- todos los IDs obligatorios tienen evidencia;
- la suite completa pasa;
- el IDE analiza un `.cps` válido y otro con errores de varias categorías;
- el árbol visual y la tabla de símbolos se pueden mostrar durante la defensa;
- la gramática y el perfil usados corresponden a la versión oficial disponible;
- los commits permiten identificar la contribución individual.

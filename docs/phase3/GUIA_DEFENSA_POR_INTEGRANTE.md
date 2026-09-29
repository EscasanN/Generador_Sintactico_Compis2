# Guía de defensa por bloques e integrante — Fase 3

Esta guía organiza la entrega por responsable para que el profesor pueda ver
qué problema resolvió cada integrante, qué archivos produjo, cómo se conecta su
bloque con los demás y qué prueba demuestra su funcionamiento.

> Estado comprobado el 7 de septiembre de 2026: **388 pruebas aprobadas**. La
> suite específica contiene **74 pruebas** y cubre los **72 programas `.cps`**
> preparados para la demostración; una prueba verifica el inventario completo y
> algunos programas se ejecutan en más de un escenario.

## 1. Cómo se dividió el trabajo

Los bloques fueron secuenciales, no cuatro implementaciones paralelas del mismo
analizador:

```text
Base: YALex/YAPar + frontend ANTLR multimodo
                    │
                    v
Daniel ── diagnósticos, tipos, valores y expresiones
                    │ entrega contratos
                    v
Nadissa ── símbolos, scopes, perfiles y motor semántico
                    │ entrega evaluador genérico
                    v
Dulce ── árbol ANTLR, Listener y adaptador semántico
                    │ entrega API integrada
                    v
Nelson ── perfil Compiscript, flujo .cps e IDE
                    │ entrega producto completo
                    v
Daniel ── auditoría final, endurecimiento y pruebas .cps
```

La última etapa fue una auditoría transversal. No significa que Daniel sea el
autor original de los bloques de Nadissa, Dulce o Nelson: verificó el sistema
integrado, corrigió riesgos de entrega y agregó evidencia ejecutable.

## 2. Resumen para presentar al profesor

| Orden | Responsable | Pregunta que resolvió | Resultado entregado |
|---:|---|---|---|
| 1 | Daniel Chet | ¿Cómo representar tipos y reportar errores sin detener el análisis? | Núcleo semántico independiente de la gramática. |
| 2 | Nadissa Vela | ¿Cómo manejar símbolos, ámbitos y acciones configurables? | Motor semántico genérico y perfiles seguros. |
| 3 | Dulce Ambrosio | ¿Cómo conectar un árbol real de ANTLR con ese motor? | Listener genérico y adaptador sintaxis→semántica. |
| 4 | Nelson Escalante | ¿Cómo convertir lo anterior en el analizador de Compiscript que usa el estudiante? | Perfil Compiscript, flujo `.cps`, resultados e IDE. |
| Auditoría | Daniel Chet | ¿Qué podía fallar al evaluar y cómo se demuestra cada requisito? | Correcciones integradas, CLI, 72 fixtures y 74 pruebas `.cps`. |

Los conteos incluidos más adelante son agrupaciones funcionales ejecutadas
sobre el estado actual, después de la auditoría. Demuestran que el subsistema de
cada bloque funciona, pero **no** representan cuántas pruebas escribió cada
persona ni un porcentaje individual de trabajo.

Evidencia en Git:

| Etapa | Commit o serie principal |
|---|---|
| Daniel — núcleo | `e74b765` |
| Nadissa — motor | `801b3bc`, `e6ca733`, `64e9c7c`, `ef1ff1b`, `3a8745b` |
| Dulce — integración | `b93c95f`, `59c80e5`, `82b28a2`, `c02e101` |
| Nelson — producto Compiscript | `2789722` |
| Daniel — auditoría final | `1fdf4da` |

Para enseñar la evidencia de un commit:

```powershell
git show --stat e74b765
git show --stat e6ca733
git show --stat 59c80e5
git show --stat 2789722
git show --stat 1fdf4da
```

## 3. Base recibida antes de los cuatro bloques

Antes del núcleo semántico ya existían:

- el modo histórico YALex + YAPar;
- inspección de gramáticas combinadas `.g4`;
- generación dinámica del Lexer y Parser de ANTLR;
- selección de regla inicial;
- el resultado sintáctico y una representación común del árbol;
- el modo ANTLR básico en la interfaz.

Esta base explica por qué la fase se concentró en la semántica y su integración,
sin reimplementar los analizadores de las fases anteriores.

### 3.1 Procedencia de los archivos compartidos

Un archivo puede haber sido creado en la base y extendido después por varias
personas. La autoría debe explicarse por cambio concreto, no atribuyendo todo el
archivo a quien hizo la última modificación:

| Archivo/capacidad | Procedencia anterior | Extensiones de esta entrega |
|---|---|---|
| `grammar_info.py` y `runner.py` | Creados por Dulce en `4961e58`, antes del bloque 1. | Dulce conservó la sesión y añadió el recorrido semántico en `b93c95f`–`82b28a2`; Daniel los verificó en la auditoría. |
| `parse_tree.py` | Archivo original de YAPar creado por Dilary Cruz en `04d8931`. | Dulce lo extendió con metadatos requeridos por ANTLR en `4961e58`. |
| `Compiscript.g4` | Creada por la identidad Git `Poposit` en `4e8ef50`. | Nelson la reestructuró para el perfil en `2789722`; Daniel la endureció en `1fdf4da`. |
| `app.py` | Creada para el IDE YAPar por `auyjos` en `57e2d97`; el modo ANTLR previo aparece bajo la identidad Git `Poposit` en `1a59a26`. | Nelson añadió el flujo semántico `.cps` en `2789722`; Daniel corrigió riesgos integrados en `1fdf4da`. |

`Poposit` se conserva como identidad de Git porque el repositorio, por sí solo,
no prueba qué nombre del equipo debe asociarse con ese alias.

# Bloque 1 — Daniel Chet

## 4. Objetivo

Daniel construyó el núcleo que responde qué tipo tiene una expresión, si una
operación o asignación es válida, cómo se promueve `integer` a `float`, si una
lista es homogénea y cómo registrar errores sin detener todo el análisis.

El núcleo no conoce Qt, ANTLR, Compiscript ni nombres de reglas gramaticales.
Por eso se puede probar directamente con objetos Python.

## 5. Archivos y responsabilidades

| Archivo | Aporte original de Daniel (`e74b765`) | Evolución posterior |
|---|---|---|
| [`diagnostics.py`](../../src/semantic/diagnostics.py) | Severidad, categoría, ubicación y colección acumulable. | Contrato conservado. |
| [`types.py`](../../src/semantic/types.py) | Jerarquía de tipos, compatibilidad y tipo común. | Endurecido en `1fdf4da` para las reglas integradas. |
| [`values.py`](../../src/semantic/values.py) | Tipo, constante, mutabilidad, símbolo y ubicación de una expresión. | Contrato conservado. |
| [`expression_actions.py`](../../src/semantic/expression_actions.py) | Literales, operadores, asignación, ternario, listas e indexación. | Ampliado/corregido durante `1fdf4da`. |
| [`test_diagnostics.py`](../../tests/semantic/test_diagnostics.py) | Pruebas del contenedor de errores. | Suite original conservada. |
| [`test_types.py`](../../tests/semantic/test_types.py) | Pruebas de compatibilidad y promoción. | Ampliadas durante `1fdf4da`. |
| [`test_expressions.py`](../../tests/semantic/test_expressions.py) | Casos positivos y negativos de expresiones. | Ampliados durante `1fdf4da`. |

## 6. Cómo funciona

1. Una acción recibe operandos como `SemanticValue`.
2. Consulta reglas como `is_assignable` o `common_type`.
3. Si es válida, devuelve un valor con el tipo resultante.
4. Si es inválida, agrega un diagnóstico y devuelve tipo `ERROR`.
5. `ERROR` permite continuar para descubrir otros fallos y evita cascadas
   innecesarias.

Ejemplo: `true + 4` llega a la acción binaria; como no son dos operandos
numéricos, produce un diagnóstico de categoría `type`.

## 7. Verificación actual del subsistema y explicación de Daniel

```powershell
python -m pytest `
  tests/semantic/test_diagnostics.py `
  tests/semantic/test_types.py `
  tests/semantic/test_expressions.py -q
```

Resultado actual: `112 passed`.

Casos visuales:

- [`TYP-01-aritmetica.cps`](../../tests/cps/validos/TYP-01-aritmetica.cps);
- [`TYP-01-aritmetica-booleana.cps`](../../tests/cps/invalidos/TYP-01-aritmetica-booleana.cps).

Esos `.cps` fueron agregados en la auditoría como evidencia integrada, pero
ejercitan directamente el núcleo creado en este bloque.

> “Mi bloque define el significado de tipos y expresiones sin depender de una
> gramática. Acumulamos diagnósticos y propagamos un tipo de recuperación para
> no detenernos en el primer error. Entregué esas APIs al motor semántico para
> que pudiera utilizarlas al recorrer cualquier árbol.”

Nadissa recibió tipos, valores, acciones y diagnósticos ya probados; no tuvo que
redefinir compatibilidad ni operadores.

# Bloque 2 — Nadissa Vela

## 8. Objetivo

Nadissa convirtió el núcleo aislado en un motor para árboles completos. Su
bloque administra identificadores, ámbitos, duplicados, funciones, control,
clases y acciones configuradas de forma segura desde un perfil.

## 9. Archivos y responsabilidades

| Archivo | Aporte original de Nadissa | Evolución posterior |
|---|---|---|
| [`symbol_table.py`](../../src/semantic/symbol_table.py) | Árbol persistente de scopes, símbolos y resolución (`801b3bc`). | Contrato conservado. |
| [`profile.py`](../../src/semantic/profile.py) | Carga, modelo, selectores y validación (`e6ca733`). | Daniel añadió identidad, fingerprint y `after_child` en `1fdf4da`. |
| [`action_registry.py`](../../src/semantic/action_registry.py) | Lista blanca de acciones (`e6ca733`). | Contrato conservado. |
| [`evaluator.py`](../../src/semantic/evaluator.py) | Contexto, recorrido e invocación (`64e9c7c`). | Daniel integró prepass/fases reforzadas en `1fdf4da`. |
| [`results.py`](../../src/semantic/results.py) | Aceptación, diagnósticos, símbolos y estadísticas (`64e9c7c`). | Contrato conservado. |
| [`actions/`](../../src/semantic/actions) | Declaraciones, funciones, control y clases (`64e9c7c`). | Algunas acciones fueron endurecidas y `composition.py` se añadió en `1fdf4da`. |

Pruebas principales: `test_symbol_table.py`, `test_profile.py`,
`test_evaluator.py`, `test_statement_actions.py`, `test_functions.py`,
`test_control_flow.py`, `test_classes.py` y `test_general_semantics.py`.

## 10. Cómo funciona

1. `SymbolTable` empieza en el scope global.
2. Cada bloque, función o clase abre un scope hijo.
3. Las declaraciones registran símbolos con nombre, tipo y mutabilidad.
4. Resolver un nombre busca localmente y después en los ancestros.
5. Un scope cerrado se conserva para que la GUI pueda mostrarlo.
6. El perfil solo contiene nombres de acciones, fases y selectores; no contiene
   código ejecutable.
7. `ActionRegistry` limita qué funciones Python puede invocar el evaluador.

```text
perfil JSON ── indica qué acción usar
ActionRegistry ── decide qué acciones existen
SemanticEvaluator ── las ejecuta con contexto y símbolos
```

Así se evitan `eval`, `exec` e imports elegidos por el JSON.

## 11. Verificación actual del subsistema y explicación de Nadissa

```powershell
python -m pytest `
  tests/semantic/test_symbol_table.py `
  tests/semantic/test_profile.py `
  tests/semantic/test_evaluator.py `
  tests/semantic/test_statement_actions.py `
  tests/semantic/test_functions.py `
  tests/semantic/test_control_flow.py `
  tests/semantic/test_classes.py `
  tests/semantic/test_general_semantics.py -q
```

Resultado actual: `70 passed`.

Casos visuales:

- [`SCP-03-bloques-anidados.cps`](../../tests/cps/validos/SCP-03-bloques-anidados.cps);
- [`SCP-03-fuera-de-alcance.cps`](../../tests/cps/invalidos/SCP-03-fuera-de-alcance.cps).

> “Mi bloque administra ámbitos y símbolos y ejecuta acciones registradas. El
> perfil es configuración segura: relaciona la forma de un árbol con operaciones
> del motor, pero no puede ejecutar código arbitrario. Los scopes se conservan
> para mostrarlos después en el IDE.”

Dulce recibió un motor que ya analizaba árboles comunes construidos en pruebas.
Quedaba conectarlo con árboles nativos reales de ANTLR.

# Bloque 3 — Dulce Ambrosio

## 12. Objetivo

Dulce creó el puente entre sintaxis y semántica: conserva el árbol nativo,
impide ejecutar semántica si la sintaxis falla, recorre ANTLR mediante un
Listener genérico y demuestra independencia con MiniCalc.

## 13. Archivos y responsabilidades

| Archivo | Aporte concreto de Dulce | Procedencia |
|---|---|---|
| [`runner.py`](../../src/antlr_mode/runner.py) | Generación/caché y, en el bloque 3, conservación de la sesión/árbol nativo. | Creado por Dulce antes del bloque 1 (`4961e58`) y extendido en `b93c95f`. |
| [`grammar_info.py`](../../src/antlr_mode/grammar_info.py) | Inspección genérica de nombre y reglas de una `.g4`. | Creado por Dulce en la base (`4961e58`) y consumido por el bloque 3. |
| [`parse_tree.py`](../../src/parser/parse_tree.py) | Metadatos de regla, alternativa, token y ubicación para ANTLR. | Archivo YAPar previo de Dilary; extendido por Dulce en `4961e58`. |
| [`antlr_listener.py`](../../src/semantic/antlr_listener.py) | Listener genérico que traduce eventos ANTLR a acciones. | Creado por Dulce en `59c80e5`. |
| [`antlr_adapter.py`](../../src/semantic/antlr_adapter.py) | API que ejecuta sintaxis primero y semántica después. | Creado por Dulce en `59c80e5`. |
| [`minicalc.semantic.json`](../../semantic_profiles/minicalc.semantic.json) | Segundo perfil para probar generalidad. | Creado por Dulce en `82b28a2`; endurecido en la auditoría. |

## 14. Cómo funciona

1. `analyze_with_g4` inspecciona la gramática.
2. Calcula una clave con versión ANTLR y contenido de la `.g4`.
3. Reutiliza Lexer y Parser si la caché coincide; si no, los genera.
4. Ejecuta Lexer/Parser y exige consumo completo de la entrada.
5. Conserva el árbol nativo y construye `ParseTreeNode` para visualización.
6. `analyze_semantics_with_g4` termina si la sintaxis fue rechazada.
7. Si es válida, verifica el perfil y recorre el árbol con
   `ParseTreeWalker` y `SemanticTreeListener`.

ANTLR se invoca con `-visitor -no-listener`. Esto evita generar un Listener
específico, pero el proyecto usa su propio Listener genérico heredado de
`antlr4.ParseTreeListener`.

[`MiniCalc.g4`](../../tests/antlr_mode/fixtures/MiniCalc.g4) demuestra que el
mismo adaptador, Listener, evaluador y acciones soportan otra forma de árbol.

## 15. Verificación actual del subsistema y explicación de Dulce

```powershell
python -m pytest `
  tests/antlr_mode `
  tests/semantic/test_antlr_adapter.py `
  tests/semantic/test_antlr_listener.py `
  tests/semantic/test_generic_grammar.py -q
```

Resultado actual: `27 passed`.

> “Mi bloque conecta el árbol real de ANTLR con el motor genérico. La sintaxis
> siempre se valida primero; solo entonces se carga el perfil y se recorre el
> árbol con nuestro Listener. MiniCalc prueba que no dependemos de nombres ni
> clases específicas de Compiscript.”

Nelson recibió la API `analyze_semantics_with_g4`, que ya devolvía sintaxis,
semántica, diagnósticos y símbolos sin depender de la GUI.

# Bloque 4 — Nelson Escalante

## 16. Objetivo

Nelson convirtió el motor genérico en el producto de Compiscript: construyó el
perfil del lenguaje, integró los archivos `.cps` y presentó árbol, diagnósticos
y tabla de símbolos en la interfaz.

## 17. Archivos y responsabilidades

| Archivo | Aporte concreto de Nelson | Procedencia/evolución |
|---|---|---|
| [`Compiscript.g4`](../../src/compiscript/grammar/Compiscript.g4) | Reestructuró alternativas para obtener un árbol consumible por el perfil. | Base de `Poposit` (`4e8ef50`), extendida por Nelson (`2789722`) y endurecida en la auditoría (`1fdf4da`). |
| [`compiscript.semantic.json`](../../semantic_profiles/compiscript.semantic.json) | Creó el mapeo de Compiscript a las acciones del motor. | Creado por Nelson (`2789722`) y ampliado en la auditoría (`1fdf4da`). |
| [`app.py`](../../src/gui/app.py) | Añadió creación/edición de `.cps`, carga de perfil, worker semántico y presentación integrada. | IDE y modo ANTLR preexistentes; extensión de Nelson en `2789722` y correcciones de auditoría en `1fdf4da`. |
| [`semantic_results.py`](../../src/gui/semantic_results.py) | Creó la vista de diagnósticos y scopes/símbolos. | Creado por Nelson en `2789722`. |
| [`parse_tree_view.py`](../../src/gui/parse_tree_view.py) | Creó el árbol sintáctico navegable. | Creado por Nelson en `2789722`. |
| [`test_end_to_end.py`](../../tests/semantic/test_end_to_end.py) | Creó la cobertura integrada de la matriz semántica. | Creado por Nelson en `2789722` y ampliado/corregido en `1fdf4da`. |
| [`test_cps_workflow.py`](../../tests/gui/test_cps_workflow.py) | Creó las pruebas IDE-01 a IDE-08 y regresión YAPar. | Creado por Nelson en `2789722` y reforzado en `1fdf4da`. |

La integración original incluyó `semantic_bridge.py`. La auditoría eliminó ese
puente duplicado y trasladó sus composiciones reutilizables a
[`actions/composition.py`](../../src/semantic/actions/composition.py), sin
cambiar el objetivo funcional del flujo diseñado por Nelson.

## 18. Cómo funciona

1. El usuario abre `Compiscript.g4`, elige `program` y carga el perfil.
2. Abre o crea un `.cps`; se analiza el contenido actual del editor.
3. `SemanticAnalysisWorker`, un `QThread`, llama al adaptador de Dulce.
4. El perfil enlaza el árbol con las acciones de Daniel y Nadissa.
5. La GUI presenta aceptación, tokens, árbol, diagnósticos y símbolos.

## 19. Quién hizo cada parte de `semantic_profiles`

| Componente | Implementación original | Modificación de auditoría (`1fdf4da`) |
|---|---|---|
| Formato, carga segura, selectores y registro de acciones | Nadissa en `e6ca733`. | Daniel añadió identidad/fingerprint, fase `after_child` y validaciones estrictas de compatibilidad/argumentos. |
| `minicalc.semantic.json` | Dulce en `82b28a2`, para demostrar generalidad. | Daniel agregó los metadatos necesarios para verificar su correspondencia con `MiniCalc.g4`. |
| `compiscript.semantic.json` | Nelson en `2789722`, como configuración completa inicial de Compiscript. | Daniel lo amplió con predeclaración, `after_child`, `foreach`, `catch`, clases y las correcciones de endurecimiento final. |

Los dos JSON no son analizadores competidores: son dos configuraciones del
mismo motor.

## 20. Verificación actual del subsistema y explicación de Nelson

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest `
  tests/semantic/test_end_to_end.py `
  tests/gui/test_cps_workflow.py -q
```

Resultado actual: `102 passed`.

Demostración visual:

```powershell
python -m src.main
```

Abrir, en orden:

1. `src/compiscript/grammar/Compiscript.g4`;
2. `semantic_profiles/compiscript.semantic.json`;
3. `tests/cps/demostracion-valida.cps`;
4. `tests/cps/demostracion-invalida.cps`.

> “Mi bloque configura el motor para la gramática de Compiscript y lo presenta
> en el IDE. El perfil no reimplementa tipos ni ámbitos; enlaza reglas del árbol
> con acciones existentes. La interfaz usa un `QThread` y presenta árbol,
> errores y tabla de símbolos.”

# Auditoría final — Daniel Chet

## 21. Propósito y correcciones

Al integrar los cuatro bloques aparecieron riesgos observables únicamente en el
flujo completo. Daniel hizo una revisión transversal sin sustituir la autoría
original. La auditoría agregó o corrigió:

- análisis del contenido actual del editor y extensión `.cps` al guardar;
- `float`, `%`, concatenación, `null` y validación de inicializadores;
- predeclaración para recursión, referencias adelantadas y miembros de clase;
- herencia, constructor implícito, `foreach` y scope de `catch`;
- fase `after_child`, fingerprint y validación estricta de perfiles;
- eliminación del puente duplicado de GUI;
- CLI `--cps`, gramática/perfil opcionales y `--syntax-only`;
- 72 programas `.cps` cubiertos por una suite de 74 pruebas, incluido un control
  automático del inventario.

Evidencia:

- [`tests/cps/README.md`](../../tests/cps/README.md);
- [`test_cps_programs.py`](../../tests/semantic/test_cps_programs.py);
- [`revision-final-daniel.md`](revision-final-daniel.md).

## 22. Pruebas y explicación de la auditoría

```powershell
python -m pytest tests/semantic/test_cps_programs.py -q
```

Resultado: `74 passed`.

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest tests -q
```

Resultado: `388 passed`.

> “La auditoría no sustituye la autoría original; verifica los contratos de los
> cuatro bloques trabajando juntos. Corregí riesgos de extremo a extremo y
> convertí los requisitos en programas `.cps` reproducibles.”

## 23. Una compilación vista por responsable

| Paso | Qué sucede | Bloque principal |
|---:|---|---|
| 1 | La GUI obtiene `.g4`, perfil, regla y texto `.cps`. | Nelson |
| 2 | El runner genera/reutiliza Lexer y Parser y construye los árboles. | Dulce |
| 3 | El adaptador valida sintaxis y después el perfil. | Dulce |
| 4 | El perfil decide qué acciones corresponden a cada nodo. | Nelson, usando el formato de Nadissa |
| 5 | El evaluador abre scopes, declara/resuelve símbolos y controla contexto. | Nadissa |
| 6 | Las expresiones consultan tipos y compatibilidad. | Daniel |
| 7 | Se acumulan diagnósticos y símbolos. | Daniel + Nadissa + Dulce |
| 8 | La GUI presenta árbol, errores y tabla de símbolos. | Nelson |
| 9 | Los fixtures `.cps`, su inventario y la regresión final comprueban el flujo integrado. | Auditoría de Daniel; las suites originales pertenecen a sus bloques respectivos. |

Nadie implementó por separado “un cuarto del lenguaje”. Cada persona produjo
una capa reutilizable que consume la entrega anterior.

## 24. Orden recomendado para la defensa

| Tiempo | Persona | Demostración |
|---:|---|---|
| 1 min | Equipo | Diagrama de bloques y diferencia `.g4`/`.cps`/perfil. |
| 2 min | Daniel | Diagnósticos, tipos y un caso TYP válido/inválido. |
| 2 min | Nadissa | Tabla de símbolos, resolución y perfil seguro. |
| 2 min | Dulce | Caché ANTLR, sintaxis antes de semántica y MiniCalc. |
| 3 min | Nelson | GUI, programa válido, inválido, árbol y símbolos. |
| 2 min | Daniel/auditoría | 72 programas `.cps`, suite de 74 pruebas y 388 pruebas totales. |

## 25. Preguntas que debería responder cada integrante

| Persona | Temas que debe dominar |
|---|---|
| Daniel | `UNKNOWN` frente a `ERROR`, promoción numérica, diagnósticos acumulables y compatibilidad. |
| Nadissa | Resolución léxica, shadowing, duplicados, registro seguro y scopes persistentes. |
| Dulce | Árbol nativo/común, sintaxis antes de semántica, Listener genérico y MiniCalc. |
| Nelson | Perfil Compiscript, contenido del editor, pestañas de resultados y `QThread`. |
| Auditoría | `ACCEPT`/`REJECT`/`ERROR`, matriz de requisitos, riesgos corregidos y fixtures. |

## 26. Reglas para explicar la autoría con precisión

- No decir que “todos hicieron de todo”; la arquitectura fue por capas.
- Diferenciar autor original de quien realizó la auditoría final.
- No usar el número de pruebas como porcentaje de trabajo: cada suite prueba un
  nivel distinto.
- Si un `.cps` de la auditoría demuestra tipos o scopes, aclarar que es evidencia
  nueva de funcionalidad implementada antes.
- Mostrar `git show --stat <commit>` si se solicita evidencia histórica.
- Conservar la autorización del profesor para trabajar como equipo de cuatro.

## 27. Documentos complementarios

- [Guía completa del funcionamiento](GUIA_COMPLETA_ENTREGA_Y_DEFENSA.md)
- [Guía rápida de pruebas](GUIA_PRUEBAS_PRESENTACION.md)
- [División formal del trabajo](DIVISION_TRABAJO.md)
- [Detalle técnico original por integrante](GUIA_IMPLEMENTACION_POR_INTEGRANTE.md)
- [Matriz de cumplimiento](MATRIZ_CUMPLIMIENTO.md)

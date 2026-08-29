# División del trabajo — Fase 3

Esta división usa cuatro bloques secuenciales y cerrados. Cada integrante
trabaja una sola vez: recibe una base aceptada, implementa todos los archivos de
su bloque, ejecuta sus pruebas y entrega una API estable al siguiente
integrante.

La descripción de archivos, clases, funciones y pruebas está en la
[guía detallada](GUIA_IMPLEMENTACION_POR_INTEGRANTE.md).

## Regla de dependencia

```text
Base multimodo existente
        │
        v
1. Daniel — núcleo semántico
        │
        v
2. Nadissa — motor semántico
        │
        v
3. Dulce — conexión ANTLR-semántica
        │
        v
4. Nelson — IDE, perfil Compiscript y entrega
```

Se permiten dependencias hacia adelante: Nadissa puede usar la entrega de
Daniel, Dulce puede usar las entregas de Daniel y Nadissa, y Nelson puede usar
las tres anteriores. No se permiten dependencias hacia atrás: una entrega no
puede dejar funciones, correcciones o integración pendientes para que su autor
regrese después.

## Base recibida por el equipo

Antes del bloque 1 ya deben estar disponibles y con pruebas:

- el modo histórico YALex + YAPar;
- la carga dinámica de gramáticas ANTLR `.g4`;
- `GrammarInfo`, `AntlrAnalysisResult` y `ParseTreeNode`;
- la selección de modo, archivo `.g4` y regla inicial en el IDE;
- las pruebas sintácticas con Compiscript y MiniCalc.

Esta base es una precondición, no una tarea intercalada entre los cuatro
bloques. Sus contratos públicos se congelan antes de que Daniel comience.

## Resumen del equipo

| Orden | Integrante | Bloque | Rama |
|---:|---|---|---|
| 1 | Daniel Chet | Diagnósticos, tipos, valores y expresiones | `feature/fase3-01-semantic-core` |
| 2 | Nadissa Vela | Símbolos, perfiles y evaluador genérico | `feature/fase3-02-semantic-engine` |
| 3 | Dulce Ambrosio | Listener ANTLR, adaptador semántico y árbol común | `feature/fase3-03-antlr-semantic` |
| 4 | Nelson Escalante | Flujo `.cps`, IDE, perfil Compiscript y entrega | `feature/fase3-04-ide-delivery` |

Cada rama se crea después de integrar la anterior. No son cuatro ramas
paralelas creadas desde el mismo punto.

## Bloque 1 — Daniel

Archivos principales:

```text
src/semantic/__init__.py
src/semantic/diagnostics.py
src/semantic/types.py
src/semantic/values.py
src/semantic/expression_actions.py
tests/semantic/test_diagnostics.py
tests/semantic/test_types.py
tests/semantic/test_expressions.py
```

Entrega el núcleo semántico independiente de ANTLR, YAPar y Qt:

- ubicaciones y diagnósticos acumulables;
- tipos primitivos, arreglos, funciones, clases, error y desconocido;
- compatibilidad, promoción numérica y tipo común;
- valores semánticos;
- acciones de literales, operadores, asignaciones, ternario e índices.

Sus pruebas cubren los IDs de tipos, listas y expresiones que le asigna
`MATRIZ_CUMPLIMIENTO.md`, siempre con caso exitoso y fallido.

Termina cuando todas sus pruebas usan datos directos, no árboles ni gramáticas,
y las firmas públicas quedan documentadas. Daniel no participa nuevamente en
la implementación de los bloques 2, 3 o 4.

## Bloque 2 — Nadissa

Archivos principales:

```text
src/semantic/symbol_table.py
src/semantic/profile.py
src/semantic/action_registry.py
src/semantic/results.py
src/semantic/evaluator.py
src/semantic/actions/
tests/semantic/test_symbol_table.py
tests/semantic/test_profile.py
tests/semantic/test_evaluator.py
tests/semantic/test_statement_actions.py
tests/semantic/test_functions.py
tests/semantic/test_control_flow.py
tests/semantic/test_classes.py
tests/semantic/test_general_semantics.py
```

Recibe la API congelada de Daniel y entrega:

- símbolos y scopes persistentes;
- carga y validación segura de perfiles JSON;
- registro de acciones sin `eval`, `exec` ni imports configurables;
- recorrido genérico de `ParseTreeNode`;
- acciones de declaraciones, funciones, control y clases;
- recursión, closures, código muerto y validación contextual;
- resultado semántico con diagnósticos y tabla de símbolos.

Sus pruebas usan árboles construidos manualmente. No dependen de una gramática,
Java, ANTLR o la GUI. Nadissa no deja el evaluador para completarlo después.

## Bloque 3 — Dulce

Archivos principales:

```text
src/antlr_mode/
src/parser/parse_tree.py
src/semantic/antlr_listener.py
src/semantic/antlr_adapter.py
semantic_profiles/minicalc.semantic.json
tests/antlr_mode/
tests/semantic/test_antlr_adapter.py
tests/semantic/test_antlr_listener.py
tests/semantic/test_generic_grammar.py
```

Recibe el motor semántico terminado y entrega la conexión completa entre una
gramática cargada en tiempo de ejecución y ese motor:

- conserva y endurece el frontend ANTLR genérico;
- garantiza metadatos suficientes en el árbol común;
- recorre el árbol nativo con `ParseTreeWalker` y un `ParseTreeListener`
  genérico, o un Visitor equivalente;
- valida el perfil contra las reglas de la gramática;
- detiene semántica cuando existen errores sintácticos;
- ejecuta el evaluador mediante un adaptador público;
- demuestra generalidad con MiniCalc u otra gramática pequeña.

No modifica las implementaciones internas de Daniel o Nadissa. Sus APIs se
consumen como contratos cerrados.

## Bloque 4 — Nelson

Archivos principales:

```text
src/gui/app.py
src/gui/antlr_results.py
src/gui/semantic_results.py
src/gui/parse_tree_view.py
semantic_profiles/compiscript.semantic.json
tests/semantic/test_end_to_end.py
tests/gui/test_cps_workflow.py
README.md
docs/phase3/
```

Recibe un flujo sintáctico y semántico funcional desde Python y entrega:

- ejecución semántica fuera del hilo principal de Qt;
- creación, apertura, edición y guardado de archivos `.cps`;
- acción para compilar el contenido completo del `.cps`;
- presentación de diagnósticos, scopes y símbolos;
- representación visual del árbol mediante nodos y aristas;
- perfil Compiscript construido únicamente con acciones registradas;
- pruebas end-to-end y regresiones de YALex + YAPar;
- documentación y procedimiento final de ejecución.

Nelson no necesita que los otros integrantes regresen para completar el perfil.
Los nombres de acciones, selectores y estructuras que puede utilizar ya deben
estar documentados por los bloques anteriores.

## Puertas de aceptación

| Puerta | Requisito para comenzar el siguiente bloque |
|---|---|
| Base → Daniel | Modos YAPar y ANTLR pasan sus pruebas y los contratos del árbol están congelados. |
| Daniel → Nadissa | Diagnósticos, tipos, valores y expresiones pasan pruebas sin dependencias externas. |
| Nadissa → Dulce | El motor analiza árboles manuales y produce diagnósticos y símbolos. |
| Dulce → Nelson | El Listener/Visitor analiza la forma de la gramática oficial y otra gramática desde Python sin modificar el motor. |
| Nelson → Entrega | El IDE compila `.cps`, muestra árbol y símbolos, y pasan todas las regresiones. |

Si una puerta no se cumple, el siguiente bloque todavía no comienza. La persona
responsable corrige su entrega antes de cerrarla; no se pospone la corrección
para el final.

## Reglas de colaboración

- Una persona propietaria por archivo durante su bloque.
- Una rama se crea desde la integración aceptada del bloque anterior.
- Cada bloque incluye pruebas exitosas y fallidas.
- Cada regla oficial conserva los IDs y evidencias de
  `MATRIZ_CUMPLIMIENTO.md`.
- El siguiente integrante consume APIs públicas, no helpers privados.
- Una API aceptada no se cambia en un bloque posterior.
- Una revisión puede realizarla cualquier integrante, pero revisar no obliga a
  volver a programar.
- Ningún archivo generado se agrega a Git.
- Ningún nombre de Compiscript se codifica dentro del motor genérico.
- Cada fixture declara gramática, regla inicial, perfil y resultado esperado.

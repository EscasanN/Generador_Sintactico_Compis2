# Revisión final de cumplimiento — Daniel Chet

Fecha: 2026-09-06  
Rama base: `feature/fase3-04-compiscript-profile` (`2789722`)  
Rama de corrección: `fix/fase3-final-compliance`

## Resultado

La implementación local satisface las reglas funcionales verificables del PDF:
tipos, ámbitos, funciones, control de flujo, clases, listas, diagnósticos,
tabla de símbolos, recorrido ANTLR y flujo del IDE. Las suites automatizadas y
los 83 casos históricos de YALex/YAPar pasan.

Quedan dos comprobaciones externas que el repositorio no puede demostrar:

1. confirmar con el profesor que `src/compiscript/grammar/Compiscript.g4` es la
   última gramática oficial;
2. conservar la evidencia de autorización para trabajar con cuatro integrantes,
   porque el PDF indica grupos de tres.

## Correcciones realizadas

- El análisis semántico de la GUI compila el contenido actual del editor aunque
  todavía no se haya guardado.
- Guardar como conserva o agrega la extensión `.cps`.
- Se agregaron literales `float` y el tipo `float` a la gramática y al perfil.
- Los inicializadores de campos y constantes de clase se infieren o se validan
  contra el tipo declarado.
- Los miembros de clase se predeclaran para evitar que el orden textual produzca
  falsos errores de atributo o método inexistente.
- Los casos negativos semánticos ahora deben superar primero la sintaxis; esto
  eliminó evidencia falsa para índices `float`.
- Las acciones auxiliares se movieron fuera de la GUI al registro público y
  genérico de `SemanticEvaluator`. Los nombres de reglas y tokens se mantienen
  exclusivamente en el perfil JSON.
- GUI y pruebas usan el adaptador público `analyze_semantics_with_g4`; se eliminó
  el puente duplicado `src/gui/semantic_bridge.py`.
- Se restauró el modo ejecutable de `scripts/run_lexer_workflow.sh`.
- README, arquitectura, plan, matriz, especificación y handoffs se actualizaron
  para describir el código realmente entregado y no afirmar una procedencia
  oficial que aún requiere confirmación externa.

## Cobertura

| Dominio | IDs verificados | Evidencia principal |
|---|---|---|
| Tipos | `TYP-01` a `TYP-06` | `tests/semantic/test_end_to_end.py`, pruebas unitarias del núcleo |
| Ámbitos | `SCP-01` a `SCP-04` | `tests/semantic/test_end_to_end.py`, `test_symbol_table.py` |
| Funciones | `FUN-01` a `FUN-05` | `tests/semantic/test_end_to_end.py`, `test_functions.py` |
| Control | `CTL-01` a `CTL-03` | casos positivos y negativos para cada construcción requerida |
| Clases | `CLS-01` a `CLS-03` | miembros, orden, constructor y `this` |
| Listas | `LST-01` y `LST-02` | homogeneidad e índices `integer`/`string`/`boolean`/`float` |
| Generales | `GEN-01` a `GEN-03` | código muerto, sentido de expresiones y duplicados |
| ANTLR | `ANT-01` a `ANT-06` | frontend, listener, árbol, consumo total y gramática de entrega |
| IDE | `IDE-01` a `IDE-08` | `tests/gui/test_cps_workflow.py` |

## Archivos de la revisión

- Código: `src/gui/app.py`, `src/semantic/actions/__init__.py`,
  `src/semantic/actions/callables.py`, `src/semantic/actions/classes.py` y el
  nuevo `src/semantic/actions/composition.py`.
- Integración: `src/compiscript/grammar/Compiscript.g4`,
  `semantic_profiles/compiscript.semantic.json` y eliminación de
  `src/gui/semantic_bridge.py`.
- Pruebas: `tests/gui/test_cps_workflow.py`,
  `tests/semantic/test_end_to_end.py` y
  `tests/semantic/test_generic_grammar.py`.
- Documentación: `README.md`, `docs/compiscript/ESPECIFICACION.md` y los
  documentos de planificación, arquitectura, matriz, decisiones y handoff bajo
  `docs/phase3/`.
- Compatibilidad: modo ejecutable restaurado para
  `scripts/run_lexer_workflow.sh`.

## Comandos y resultados

```text
py -3.14 -m pytest tests/semantic/test_diagnostics.py -q  -> 5 passed
py -3.14 -m pytest tests/semantic/test_types.py -q        -> 36 passed
py -3.14 -m pytest tests/semantic/test_expressions.py -q  -> 65 passed
py -3.14 -m pytest tests/semantic -q                      -> 259 passed
py -3.14 -m pytest tests/antlr_mode -q                    -> 12 passed
py -3.14 -m pytest tests/gui -q                           -> 11 passed
py -3.14 -m pytest -q                                     -> 282 passed
casos CLI YALex/YAPar                                     -> 75 ACCEPT, 8 REJECT
py -3.14 -m compileall -q src tests                       -> correcto
py -3.14 -m pip check                                     -> sin dependencias rotas
git diff --check                                          -> correcto
```

Entorno verificado: OpenJDK 21.0.11, Graphviz 15.0.0, runtime ANTLR 4.13.2 y
PyQt6 importables. `output/` permanece ignorado y sin archivos rastreados.

## Decisiones semánticas relevantes

- `integer` se promueve a `float`; no se permite el estrechamiento inverso.
- `+` es aritmético y no concatena cadenas, conforme al mínimo explícito del
  PDF.
- `switch` exige condición booleana, siguiendo literalmente el PDF.
- La gramática exige inicializador sintáctico para `const`; la acción semántica
  conserva la validación defensiva para árboles manuales.
- La herencia, la inferencia de `foreach` y el parámetro de `catch` no forman
  parte del mínimo semántico enumerado por el PDF y permanecen documentados
  como capacidades no mínimas.

## Estado de Git

No se realizó commit ni push durante esta revisión. El cambio de modo del script
Bash aparece preparado en el índice porque Git para Windows representa ese bit
mediante el índice; el resto de cambios permanece sin preparar para revisión.

Salida final de `git status --short`:

```text
 M README.md
 M docs/compiscript/ESPECIFICACION.md
 M docs/phase3/ARQUITECTURA.md
 M docs/phase3/DIVISION_TRABAJO.md
 M docs/phase3/MATRIZ_CUMPLIMIENTO.md
 M docs/phase3/PLAN.md
 M docs/phase3/README.md
 M docs/phase3/REGLAS_Y_DECISIONES.md
 M docs/phase3/bloque3-dulce-entrega.md
 M docs/phase3/bloque4-nelson-entrega.md
M  scripts/run_lexer_workflow.sh
 M semantic_profiles/compiscript.semantic.json
 M src/compiscript/grammar/Compiscript.g4
 M src/gui/app.py
 D src/gui/semantic_bridge.py
 M src/semantic/actions/__init__.py
 M src/semantic/actions/callables.py
 M src/semantic/actions/classes.py
 M tests/gui/test_cps_workflow.py
 M tests/semantic/test_end_to_end.py
 M tests/semantic/test_generic_grammar.py
?? docs/phase3/GUIA_PRUEBAS_PRESENTACION.md
?? docs/phase3/revision-final-daniel.md
?? src/semantic/actions/composition.py
```

Nombre sugerido del commit:

```text
fix(phase3): align final Compiscript delivery with project requirements
```

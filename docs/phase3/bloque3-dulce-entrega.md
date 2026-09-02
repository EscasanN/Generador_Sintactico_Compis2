# Entrega del bloque 3 — Dulce Ambrosio

## Alcance implementado

El bloque conecta el frontend ANTLR con el motor semántico genérico sin
depender de clases generadas para Compiscript.

- `AntlrAnalysisResult` conserva un `AntlrRuntimeSession` opaco con el árbol
  nativo y los nombres de las reglas.
- `SemanticTreeListener` hereda de `antlr4.ParseTreeListener` y ejecuta los
  bindings del perfil durante un recorrido con `ParseTreeWalker`.
- `analyze_semantics_with_g4` analiza sintaxis primero, detiene la etapa
  semántica ante errores, valida el perfil y devuelve ambos resultados.
- `source_path` se propaga a ubicaciones semánticas basadas en 1.
- MiniCalc reutiliza las acciones de literales y operadores del motor ya
  existente. TinyNumber demuestra que el mismo adaptador procesa dos
  gramáticas y perfiles distintos consecutivamente.

No se modificaron los algoritmos internos del motor semántico ni la GUI.

## API para el bloque de Nelson

```python
from src.semantic.antlr_adapter import analyze_semantics_with_g4

run = analyze_semantics_with_g4(
    grammar_path="ruta/Grammar.g4",
    source=source_text,
    profile_path="ruta/grammar.semantic.json",
    start_rule="root",
    source_path="ruta/programa.cps",
)
```

El consumidor puede usar:

- `run.accepted`: aceptación conjunta de sintaxis y semántica;
- `run.syntax_result.tree`: `ParseTreeNode` común para visualización;
- `run.syntax_result.diagnostics`: errores de Lexer o Parser;
- `run.semantic_result`: valor, tabla de símbolos, estadísticas y
  diagnósticos semánticos; es `None` si la sintaxis fue rechazada.

Los errores de configuración, perfiles incompatibles o árboles inconsistentes
se reportan mediante `SemanticAdapterError`. La GUI no necesita acceder al
árbol ANTLR nativo.

## Evidencia del bloque

| Requisito | Evidencia |
|---|---|
| `ANT-01` | `test_compiscript_g4_accepts_valid_complete_program` genera y ejecuta la gramática oficial. |
| `ANT-02` | `test_minicalc_semantics_accepts_arithmetic_with_native_walker` recorre el árbol nativo mediante el adaptador. |
| `ANT-03` | `test_compiscript_g4_accepts_valid_complete_program` verifica regla, token y coordenadas del árbol común. |
| `ANT-04` | `test_main_window_exposes_both_modes_and_g4_rules` renderiza el árbol; la presentación final queda en el bloque 4. |
| `ANT-05` | `test_reports_input_left_after_selected_start_rule` rechaza tokens sobrantes. |
| `ANT-06` | `test_official_compiscript_grammar_walks_with_generic_listener` genera y recorre la gramática oficial con un perfil de humo exclusivo de pruebas. |
| Generalidad | `test_same_adapter_handles_two_unrelated_grammars_consecutively` ejecuta MiniCalc y TinyNumber sin cambiar Python. |

También se cubren la reutilización de caché, regla inicial inexistente, perfil
incompatible, supresión de semántica tras un error sintáctico y resultados
semánticos positivos y negativos de MiniCalc.

## Verificación

La verificación ligera, que no requiere Java ni instalar paquetes, se ejecuta
con:

```text
python -m compileall -q src tests
git diff --check
```

Las pruebas unitarias aisladas del adaptador, listener y perfiles también
pueden ejecutarse sin generar parsers. Para la validación integral se requiere
lo declarado en `requirements.txt`, Java y Graphviz en `PATH`. En el primer uso
el frontend descarga ANTLR 4.13.2 en la caché ignorada y verifica su SHA-256.

```text
python -m pip install -r requirements.txt
python -m pytest tests/antlr_mode tests/semantic -q
python -m pytest -q
```

La validación final del 1 de septiembre de 2026 usó Python 3.12, el runtime
ANTLR 4.13.2, Temurin Java 17.0.20.1 y Graphviz 16.0.0. Tanto la suite del
bloque como la colección completa del repositorio terminaron con `195 passed`.
También pasaron la compilación de bytecode y `git diff --check`; no fue
necesario modificar código como resultado de esta ejecución.

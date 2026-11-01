# Procedencia de reutilización

Referencia: https://github.com/EscasanN/Generador_Sintactico_Compis2.git, rama `feature/proyecto2-codegen`, commit `6791fefc9a61f10e528504b537854a56f705e187`.

El repositorio se consultó en modo lectura. Su cambio local preexistente en `tests/cps/codegen/validos/LST-01-listas.cps` se preservó. No se copió el proyecto, su entorno, perfiles, gramática Compiscript, semántica de clases, TAC ni registros de activación. No se encontró archivo LICENSE en la raíz consultada; se registra procedencia sin atribuir una licencia no confirmada al código del equipo.

| Origen | Uso en este proyecto | Adaptación |
|---|---|---|
| `src/antlr_mode/parse_tree.py` | `models.ParseTreeNode` | Modelo dataclass neutral; ubicación agrupada; sin alternativas específicas |
| `src/antlr_mode/runner.py` | `frontend.parse_sql` y script de generación | Patrón de listeners, tokens, conversión recursiva y SHA oficial; se eliminó generación/descarga durante análisis |
| `src/semantic/diagnostics.py` | `models.SourceLocation`, `Diagnostic` | Ubicación desde 1 y diagnósticos sin imprimir; categorías propias del pipeline SQL |
| `src/gui/parse_tree_view.py` | Vista de árbol de `gui` | Patrón QTreeWidget; presentación directa sin archivos Graphviz |
| `src/antlr_mode/parse_tree_visualizer.py` | Evaluado, no copiado | Renderizar a archivo no es parte del análisis puro; árbol Qt satisface visualización |
| `src/gui/app.py` | Worker y documentos de `gui` | Patrones de señal, revisión y guardar/descartar/cancelar, reimplementados para API SQL |
| `tests/antlr_mode`, `tests/gui/test_document_safety.py` | Patrones de prueba | Parametrización válido/inválido, EOF, coordenadas, cancelación y pruebas Qt offscreen; fixtures SQL nuevos |

ANTLR 4.13.2: https://www.antlr.org/, generador externo permitido por el enunciado. Los módulos bajo `generated` son generados por ANTLR a partir de la gramática SQL propia; se conserva su encabezado. La herramienta no se requiere en runtime. El JAR utilizado para generar se leyó de la caché del proyecto de referencia y se verificó con SHA-256 `eae2dfa119a64327444672aff63e9ec35a20180dc5b8090b7a6ab85125df4d76`.

Skills consultadas en `.agents/skills` de la referencia: test-driven-development, python-patterns, requesting-code-review y sus referencias de pruebas/revisión. Se usan como método de desarrollo, sin convertirse en dependencia del proyecto.

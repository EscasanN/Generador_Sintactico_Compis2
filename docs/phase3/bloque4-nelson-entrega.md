# Entrega del bloque 4 — Nelson Escalante

## Alcance implementado

El bloque entrega el perfil semántico de la gramática Compiscript disponible y el
IDE que abre, edita, guarda y compila archivos `.cps` mostrando árbol,
diagnósticos y tabla de símbolos.

- `src/compiscript/grammar/Compiscript.g4`: reescrita con alternativas
  etiquetadas de aridad fija y recursión a la izquierda (mismo lenguaje
  aceptado, árbol de derivación regular). Justificación completa, con fecha,
  en `docs/phase3/REGLAS_Y_DECISIONES.md`.
- `semantic_profiles/compiscript.semantic.json`: perfil declarativo con
  bindings que cubren declaraciones, control de flujo, funciones, clases,
  arreglos y toda la cadena de expresiones de la gramática de entrega.
- `src/semantic/actions/composition.py`: composiciones genéricas registradas
  por el motor. Todos los nombres de reglas y tokens se reciben desde el
  perfil; la GUI no contiene acciones semánticas.
- `src/gui/parse_tree_view.py` y `src/gui/semantic_results.py`: vista de árbol
  navegable y panel de diagnósticos + tabla de símbolos por entorno.
- `src/gui/app.py`: extendido (sin romper la API existente) con el flujo
  `.cps` completo: nuevo archivo, abrir, editar, guardar, "Guardar como",
  cargar un perfil semántico opcional y compilar (sintaxis + semántica) en un
  hilo de trabajo (`SemanticAnalysisWorker`) separado del hilo de Qt.
- `tests/semantic/test_end_to_end.py`: pruebas positivas y negativas
  por cada ID obligatorio de `MATRIZ_CUMPLIMIENTO.md` (TYP, SCP, FUN, CTL,
  CLS, LST, GEN) más dos de integración ANTLR (ANT-06), todas ejecutando la
  gramática y el perfil reales, nunca un árbol manual.
- `tests/gui/test_cps_workflow.py`: pruebas cubriendo IDE-01 a IDE-08 sobre
  la ventana real, además de regresiones (modo YAPar intacto, ANTLR y
  Compiscript ejecutados consecutivamente en la misma ventana).

## Por qué la gramática de ejemplo tuvo que ajustarse

El selector de perfiles (`src/semantic/profile.py`, congelado en el bloque 2)
solo puede leer un hijo por índice fijo, un terminal directo por tipo de
token, el texto concatenado del nodo actual, o todos los hijos a la vez. La
gramática de ejemplo combinaba partes opcionales independientes en una sola
alternativa sin etiquetar (p. ej. `variableDeclaration: ... typeAnnotation?
initializer? ';'`), lo que produce árboles de aridad variable que ese selector
no puede consumir de forma segura. Se verificó empíricamente, con el JAR real
de ANTLR y volcados de árbol, que la alternativa viable sin pedir cambios a un
bloque anterior era reestructurar la gramática en alternativas etiquetadas de
aridad fija y forma recursiva a la izquierda — la misma técnica que ya usa
`MiniCalc.g4`. El detalle regla por regla, con fecha, está en
`docs/phase3/REGLAS_Y_DECISIONES.md`.

## Composiciones de acciones del registro público

Durante la construcción del perfil aparecieron dos huecos genuinos, no
específicos de Compiscript, en el conjunto de acciones publicado:

1. Construir una tupla limpia de valores a partir de una lista separada por
   comas (argumentos de llamada, elementos de arreglo, parámetros con nombre y
   tipo) — ningún selector aplana ese tipo de lista, y la única acción que
   filtra separadores con seguridad (`function.call`) no expone el resultado
   intermedio para reutilizarlo en otra acción.
2. Componer dos acciones ya publicadas sobre el mismo nodo (resolver un
   identificador o un acceso a miembro, y luego validar la asignación) — un
   selector solo lee el resultado ya calculado de un hijo, nunca el resultado
   de una acción hermana sobre el mismo nodo.

`src/semantic/actions/composition.py` resuelve ambos con funciones pequeñas
que **delegan** en `ExpressionActions`, `resolve_identifier`,
`access_member`, `declare_function`, `declare_method` y `validate_sequence`
reales; ninguna reimplementa su lógica. Se registran con
`register_builtin_actions`, mientras los detalles sintácticos se reciben como
argumentos del perfil. Por ello el IDE y las pruebas usan directamente
`analyze_semantics_with_g4`, sin un adaptador duplicado en `src/gui`.

La revisión posterior de cumplimiento también agregó predeclaración de miembros
para eliminar falsos errores por orden textual, validación de inicializadores
de campos y constantes de clase, y literales `float` exigidos por el PDF.

## API para ejecutar Compiscript

```python
from src.semantic.antlr_adapter import analyze_semantics_with_g4

run = analyze_semantics_with_g4(
    grammar_path="src/compiscript/grammar/Compiscript.g4",
    source=source_text,
    profile_path="semantic_profiles/compiscript.semantic.json",
    start_rule="program",
    source_path="programa.cps",
)

run.accepted                       # sintaxis y semántica aceptadas
run.syntax_result.tree             # ParseTreeNode común, para árbol o Graphviz
run.semantic_result.diagnostics    # categoría, severidad, línea, columna
run.semantic_result.symbol_table   # entornos global/función/clase/bloque
```

## Cobertura frente a `MATRIZ_CUMPLIMIENTO.md`

| Dominio | IDs | Evidencia |
|---|---|---|
| Sistema de tipos | TYP-01..06 | `tests/semantic/test_end_to_end.py::test_typ_*` |
| Ámbito | SCP-01..04 | `tests/semantic/test_end_to_end.py::test_scp_*` |
| Funciones | FUN-01..05 | `tests/semantic/test_end_to_end.py::test_fun_*` |
| Control de flujo | CTL-01..03 | `tests/semantic/test_end_to_end.py::test_ctl_*` |
| Clases | CLS-01..03 | `tests/semantic/test_end_to_end.py::test_cls_*` |
| Listas | LST-01..02 | `tests/semantic/test_end_to_end.py::test_lst_*` |
| Reglas generales | GEN-01..03 | `tests/semantic/test_end_to_end.py::test_gen_*` |
| Integración ANTLR (repetida con la gramática final) | ANT-06 | `tests/semantic/test_end_to_end.py::test_ant_06_*` |
| IDE | IDE-01..08 | `tests/gui/test_cps_workflow.py` |

Cada fila de la matriz tiene exactamente un caso exitoso y uno fallido
nombrado con su identificador, ejecutando siempre la gramática y el perfil
reales (`analyze_semantics_with_g4`), nunca una acción aislada con un
árbol manual.

## Compatibilidad reforzada

Ver la sección fechada 2026-09-06 de `docs/phase3/REGLAS_Y_DECISIONES.md` para
el detalle completo. La versión reforzada incluye `%`, concatenación de dos
cadenas, referencias anulables, constructor implícito sin argumentos,
predeclaración global, herencia, inferencia de `foreach` y parámetro de `catch`
con scope propio. Una `.g4` externa continúa necesitando su perfil para análisis
semántico; sin él, la nueva CLI ejecuta solo sintaxis.

## Verificación

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/antlr_mode -q   # 12 passed
QT_QPA_PLATFORM=offscreen python -m pytest tests/semantic -q     # 259 passed
QT_QPA_PLATFORM=offscreen python -m pytest tests/gui -q          # 11 passed
QT_QPA_PLATFORM=offscreen python -m pytest -q                    # 282 passed
python -m compileall -q src tests                                # sin errores
```

`output/antlr/` (incluida la caché del `.jar` de ANTLR) permanece fuera de
control de versiones, tal como especifica `.gitignore`.

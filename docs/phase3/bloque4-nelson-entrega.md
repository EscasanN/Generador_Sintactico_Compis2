# Entrega del bloque 4 — Nelson Escalante

## Alcance implementado

El bloque entrega el perfil semántico oficial de Compiscript, las extensiones
mínimas necesarias para poder expresarlo con el motor genérico congelado, y el
IDE que abre, edita, guarda y compila archivos `.cps` mostrando árbol,
diagnósticos y tabla de símbolos.

- `src/compiscript/grammar/Compiscript.g4`: reescrita con alternativas
  etiquetadas de aridad fija y recursión a la izquierda (mismo lenguaje
  aceptado, árbol de derivación regular). Justificación completa, con fecha,
  en `docs/phase3/REGLAS_Y_DECISIONES.md`.
- `semantic_profiles/compiscript.semantic.json`: perfil declarativo con 79
  bindings que cubren declaraciones, control de flujo, funciones, clases,
  arreglos y toda la cadena de expresiones de la gramática oficial.
- `src/gui/semantic_bridge.py`: módulo propio de Nelson con un pequeño
  conjunto de acciones adicionales (`x.*`), neutras respecto a Compiscript,
  que solo componen o delegan en las funciones ya publicadas por Daniel y
  Nadissa. No modifica ningún archivo de un bloque anterior.
- `src/gui/parse_tree_view.py` y `src/gui/semantic_results.py`: vista de árbol
  navegable y panel de diagnósticos + tabla de símbolos por entorno.
- `src/gui/app.py`: extendido (sin romper la API existente) con el flujo
  `.cps` completo: nuevo archivo, abrir, editar, guardar, "Guardar como",
  cargar un perfil semántico opcional y compilar (sintaxis + semántica) en un
  hilo de trabajo (`SemanticAnalysisWorker`) separado del hilo de Qt.
- `tests/semantic/test_end_to_end.py`: 68 pruebas, una exitosa y una fallida
  por cada ID obligatorio de `MATRIZ_CUMPLIMIENTO.md` (TYP, SCP, FUN, CTL,
  CLS, LST, GEN) más dos de integración ANTLR (ANT-06), todas ejecutando la
  gramática y el perfil reales, nunca un árbol manual.
- `tests/gui/test_cps_workflow.py`: 9 pruebas cubriendo IDE-01 a IDE-08 sobre
  la ventana real, más dos de regresión (modo YAPar intacto, ANTLR y
  Compiscript ejecutados consecutivamente en la misma ventana).

No se modificó ningún archivo de `src/semantic/` fuera de lectura, ni
`src/antlr_mode/`, ni `src/parser/`.

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

## Extensiones de acciones (`x.*`)

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

`src/gui/semantic_bridge.py` resuelve ambos con funciones de unas pocas
líneas que **delegan** en `ExpressionActions`, `resolve_identifier`,
`access_member`, `declare_function`, `declare_method` y `validate_sequence`
reales — ninguna reimplementa su lógica. Se registran bajo el prefijo `x.`
para que cualquiera pueda auditar, con un `grep "x\."` sobre el perfil, cuáles
bindings dependen de esta extensión y cuáles usan exclusivamente el motor
congelado. `analyze_semantics_with_extensions` reutiliza sin cambios
`analyze_with_g4`, `load_profile`, `validate_profile`, `SemanticTreeListener`
y el parámetro `registry=` ya existente de `SemanticEvaluator` — un punto de
extensión que Nadissa ya había dejado disponible — para inyectar el registro
extendido. El IDE y las pruebas de Compiscript siempre pasan por esta función,
no por `analyze_semantics_with_g4` directamente, porque el perfil de
Compiscript referencia acciones `x.*` que el registro por defecto no tiene.

## API para ejecutar Compiscript

```python
from src.gui.semantic_bridge import analyze_semantics_with_extensions

run = analyze_semantics_with_extensions(
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
reales (`analyze_semantics_with_extensions`), nunca una acción aislada con un
árbol manual.

## Limitaciones documentadas

Ver la sección fechada 2026-09-05 de `docs/phase3/REGLAS_Y_DECISIONES.md`
para el detalle completo; en resumen:

- No hay concatenación `string + string` (`ExpressionActions.binary`,
  congelada, solo acepta operandos numéricos para `+`).
- No hay herencia real: `class B : A` se acepta sintácticamente pero el
  vínculo se ignora (`declare_class`/`construct` no aceptan superclase).
- `new Tipo()` exige que la clase declare un método llamado literalmente
  `constructor` (comportamiento de `construct`, congelado).
- `foreach` y `try/catch` funcionan de forma mínima (no bloquean el análisis)
  pero sin inferencia de tipo de elemento ni scope propio para el parámetro
  de `catch` — ambos marcados "no mínimos" en `MATRIZ_CUMPLIMIENTO.md`.
- El inicializador de un campo de clase no se compara contra su tipo
  declarado (`declare_field` congelada no tiene parámetro `initializer`).
- El operador `%` se acepta sintácticamente pero produce un diagnóstico de
  "operador no soportado" (no está en la matriz mínima).

## Verificación

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/antlr_mode -q   # 12 passed
QT_QPA_PLATFORM=offscreen python -m pytest tests/semantic -q     # 251 passed
QT_QPA_PLATFORM=offscreen python -m pytest tests/gui -q          # 9 passed
QT_QPA_PLATFORM=offscreen python -m pytest -q                    # 272 passed
python -m compileall -q src tests                                # sin errores
```

`output/antlr/` (incluida la caché del `.jar` de ANTLR) permanece fuera de
control de versiones, tal como especifica `.gitignore`.

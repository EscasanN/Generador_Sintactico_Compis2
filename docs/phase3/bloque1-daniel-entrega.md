# Entrega del Bloque 1 — Daniel Chet

## Resumen

Se implementó el núcleo semántico independiente de ANTLR, YAPar, PyQt6,
perfiles, tablas de símbolos y nombres de reglas gramaticales. La entrega
incluye diagnósticos acumulables, una jerarquía inmutable de tipos, valores
semánticos neutrales y acciones para literales, operadores, asignaciones,
ternarios, arreglos e índices.

Los errores semánticos se agregan a `DiagnosticBag` y producen valores de
recuperación sin imprimir ni lanzar excepciones durante el análisis normal.
`ERROR` y `UNKNOWN` se reconocen también dentro de arreglos y firmas de
función. Un `UNKNOWN` difiere la validación únicamente si las formas podrían
coincidir; no oculta incompatibilidades ya demostrables entre tipos conocidos.

## Archivos creados

- `src/semantic/__init__.py`
- `src/semantic/diagnostics.py`
- `src/semantic/types.py`
- `src/semantic/values.py`
- `src/semantic/expression_actions.py`
- `tests/semantic/test_diagnostics.py`
- `tests/semantic/test_types.py`
- `tests/semantic/test_expressions.py`
- `docs/phase3/bloque1-daniel-entrega.md`

No se modificaron archivos asignados a Nadissa, Dulce o Nelson. No fue
necesario agregar fixtures.

## APIs públicas entregadas

### Diagnósticos

- `DiagnosticSeverity`: `ERROR`, `WARNING`.
- `DiagnosticCategory`: `TYPE`, `SCOPE`, `FUNCTION`, `CONTROL_FLOW`, `CLASS`,
  `ARRAY`, `GENERAL`.
- `SourceLocation(line, column, end_line=None, end_column=None,
  source_path=None)`: ubicación inmutable con coordenadas públicas basadas en
  1; rechaza coordenadas menores que 1.
- `Diagnostic(category, severity, message, location)`: registro inmutable.
- `DiagnosticBag`: `add`, `extend`, `items`, `has_errors`, iteración y longitud.
  `items` es un snapshot inmutable y `add` devuelve el diagnóstico agregado.

### Tipos

- Clases: `Type`, `PrimitiveType`, `ArrayType`, `FunctionType`, `ClassType`,
  `ErrorType`, `UnknownType`.
- Singletons: `INTEGER`, `FLOAT`, `STRING`, `BOOLEAN`, `NULL`, `VOID`, `ERROR`,
  `UNKNOWN`.
- Funciones: `type_from_name`, `is_assignable`, `common_type`, `is_numeric`,
  `is_boolean`.
- `type_from_name` acepta un mapping o callable neutral para resolver clases y
  devuelve `UNKNOWN` si el nombre no se puede resolver.

### Valores

- `SymbolReference`: protocolo estructural neutral basado únicamente en
  `name: str`.
- `SemanticValue`: conserva `type`, `constant_value`, `assignable`, `mutable`,
  `symbol` y `location` en un registro inmutable.

### Acciones de expresiones

- `ExpressionActions(diagnostics)`.
- `literal(kind, text, location)`.
- `unary(operator, operand, location)`.
- `binary(operator, left, right, location)`.
- `assignment(target, value, location)`.
- `ternary(condition, true_value, false_value, location)`.
- `array_literal(elements, location)`.
- `index(container, index, location)`.

Todas las clases, funciones y métodos públicos tienen type hints y docstrings
con parámetros, retorno y política de errores.

## Matriz de cobertura

| ID | Caso exitoso | Caso fallido |
|---|---|---|
| `TYP-01` | `test_typ_01_success_arithmetic_accepts_only_numeric_operands` | `test_typ_01_failure_arithmetic_rejects_non_numeric_primitives` |
| `TYP-02` | `test_typ_02_success_logical_operators_accept_boolean_operands` | `test_typ_02_failure_logical_binary_rejects_non_boolean_operands` y `test_typ_02_failure_logical_not_rejects_non_boolean_operand` |
| `TYP-03` | `test_typ_03_success_comparisons_accept_compatible_types` | `test_typ_03_failure_comparisons_reject_incompatible_types` |
| `TYP-04` | `test_typ_04_success_assignment_accepts_compatible_mutable_targets` | `test_typ_04_failure_assignment_rejects_incompatible_values` |
| `TYP-06` | `test_typ_06_success_list_structure_uses_a_valid_promoted_type` | `test_typ_06_failure_list_structure_rejects_incompatible_depth` |
| `LST-01` | `test_lst_01_success_homogeneous_list_preserves_element_type` | `test_lst_01_failure_heterogeneous_list_reports_array_diagnostic` |
| `LST-02` | `test_lst_02_success_integer_index_returns_assignable_element_type` y caso anidado | `test_lst_02_failure_rejects_every_known_noninteger_index` |
| `GEN-02` | `test_gen_02_success_numeric_multiplication_has_semantic_meaning` | `test_gen_02_failure_numeric_operations_reject_semantically_meaningless_values` |

La suite también cubre múltiples diagnósticos, ubicaciones basadas en 1,
igualdad y representación, promoción numérica, clases y funciones, propagación
simple y compuesta de `ERROR`/`UNKNOWN`, constantes, literales inválidos,
ternarios, listas vacías/anidadas e indexación asignable.

## Comandos ejecutados y resultados

| Comando | Resultado final |
|---|---|
| `python -m pytest tests/semantic/test_diagnostics.py -q` | `5 passed` |
| `python -m pytest tests/semantic/test_types.py -q` | `36 passed` |
| `python -m pytest tests/semantic/test_expressions.py -q` | `65 passed` |
| `python -m pytest -q` | `115 passed` |
| `git diff --check` | Sin errores |
| Verificación `git diff --no-index --check` de archivos nuevos | Sin errores |
| Búsqueda de imports, llamadas y nombres prohibidos con `rg` | Sin coincidencias |
| Auditoría de IDs obligatorios con `rg` | Éxito y fallo localizables para los ocho IDs |
| Auditoría de firmas/docstrings con `inspect` | Sin faltantes públicos |
| Revisión independiente de código | `Ready to merge: Yes`; sin hallazgos críticos o importantes |

La primera ejecución completa encontró cinco fallos de la base ANTLR porque el
entorno no tenía `antlr4-python3-runtime`. Se instaló exactamente la versión
`4.13.2` ya declarada en `requirements.txt`, sin modificar el repositorio, y la
suite completa pasó. No se hizo commit ni push.

## Decisiones y supuestos semánticos

- `+` es exclusivamente aritmético; no se habilita concatenación de strings
  porque el PDF confirma únicamente operandos `integer` o `float`.
- La promoción permitida es `integer` a `float`; no se permite narrowing de
  `float` a `integer`.
- `/` usa el tipo numérico común: dos operandos `integer` producen tipo
  estático `integer`. La semántica de ejecución no pertenece a este bloque.
- Los arreglos son invariantes en asignación. La inferencia de un literal sí
  calcula recursivamente un tipo común, incluida promoción numérica.
- Las funciones requieren firma estructural exacta. Las clases permiten
  asignación de subclase a ancestro y `common_type` encuentra el ancestro común
  más cercano.
- `NULL` solo es compatible con `NULL` hasta que exista una regla confirmada de
  nulabilidad para clases o arreglos.
- `ERROR` domina y se propaga, incluso dentro de tipos compuestos, sin generar
  diagnósticos en cascada.
- `UNKNOWN` no se considera compatible con un tipo concreto. Las acciones lo
  propagan sin diagnóstico cuando la compatibilidad depende de información no
  resuelta, pero conservan errores demostrables entre restricciones conocidas.
- Un arreglo vacío tiene tipo `UNKNOWN[]`. El anidamiento preserva cada
  dimensión conocida.
- La indexación válida hereda `assignable`, `mutable` y `symbol` del contenedor
  para permitir que el bloque 2 valide asignaciones a elementos.
- Solo los literales conservan `constant_value`; este bloque no realiza
  plegado constante de operadores.
- Los signos numéricos se modelan como operadores unarios, no como parte del
  texto del literal.

## Estado de Git

Rama final:

```text
feature/fase3-01-semantic-core
```

Salida final de `git status --short`:

```text
 M README.md
 M docs/compiscript/ESPECIFICACION.md
 M docs/phase3/ARQUITECTURA.md
 M docs/phase3/DIVISION_TRABAJO.md
 M docs/phase3/GUIA_IMPLEMENTACION_POR_INTEGRANTE.md
 M docs/phase3/PLAN.md
 M docs/phase3/README.md
 M docs/phase3/REGLAS_Y_DECISIONES.md
?? docs/phase3/MATRIZ_CUMPLIMIENTO.md
?? docs/phase3/bloque1-daniel-entrega.md
?? skills-lock.json
?? src/semantic/__init__.py
?? src/semantic/diagnostics.py
?? src/semantic/expression_actions.py
?? src/semantic/types.py
?? src/semantic/values.py
?? tests/semantic/test_diagnostics.py
?? tests/semantic/test_expressions.py
?? tests/semantic/test_types.py
```

Los cambios en `README.md`, los documentos de arquitectura/plan/especificación,
`MATRIZ_CUMPLIMIENTO.md` y `skills-lock.json` ya existían antes de comenzar el
bloque y se conservaron intactos. Los únicos archivos creados por esta entrega
son los nueve enumerados en la sección “Archivos creados”.

## Commit sugerido

```text
feat(semantic): implement parser-independent phase 3 core
```

# Guía detallada de implementación por integrante — Fase 3

## Objetivo y regla principal

El proyecto debe conservar el generador YALex + YAPar de las fases 1 y 2 y,
además, permitir cargar una gramática ANTLR `.g4` desde el mismo IDE. Cambiar
de gramática no debe requerir editar, regenerar manualmente ni recompilar el
código fuente del proyecto.

`Compiscript.g4` es una entrada de ejemplo y una prueba de aceptación, no una
dependencia codificada dentro del sistema.

## Invariantes obligatorios

- El modo **YALex + YAPar** continúa aceptando `.yal`, `.yapar` y entrada
  exactamente como antes.
- El modo **ANTLR (.g4)** recibe gramática, regla inicial y entrada desde el IDE.
- Los archivos generados van a `output/antlr/`, nunca a `src/` ni a Git.
- Ningún módulo semántico importa clases generadas para Compiscript.
- El árbol común conserva regla, alternativa, token y ubicación.
- Una segunda gramática con nombres distintos debe funcionar sin cambiar Python.
- LR(0), SLR, LALR, LL(1) y Steps siguen perteneciendo al motor YAPar.
- Descarga, generación, análisis y renderizado se ejecutan fuera del hilo de Qt.

## Estado de la base

| Capacidad | Estado |
|---|---|
| Detectar nombre, tipo y reglas de una gramática `.g4` | Implementado |
| Validar el nombre del archivo | Implementado |
| Seleccionar regla inicial desde el IDE | Implementado |
| Descargar ANTLR 4.13.2 durante el primer uso | Implementado |
| Generar Python en caché por hash | Implementado |
| Cargar Lexer y Parser dinámicamente | Implementado |
| Recolectar errores léxicos y sintácticos | Implementado |
| Convertir a `ParseTreeNode` | Implementado |
| Mostrar tokens, árbol y diagnósticos | Implementado |
| Probar Compiscript y MiniCalc sin cambiar el motor | Implementado |
| Análisis semántico dirigido por configuración | Pendiente |
| Tabla de símbolos semántica | Pendiente |
| Perfil semántico de Compiscript | Pendiente |

## Flujos que deben coexistir

```text
MODO 1 — Fases 1 y 2

.yal ──> Scanner/Resolver ──> NFA ──> DFA ──> DFA mínimo
                                  │
.yapar ──> Grammar ──> LR(0)/SLR/LALR/LL(1)
                                  │
entrada ──────────────────────────┴──> árboles, pasos y resultados


MODO 2 — ANTLR

.g4 ──> inspección ──> generación/caché ──> Lexer + Parser dinámicos
                                                │
entrada + regla inicial ────────────────────────┴──> tokens, árbol y errores
                                                        │
                                                        v
                                              árbol común ParseTreeNode
                                                        │
                                                        v
                                          motor semántico configurable
```

Un modo no reemplaza al otro. Comparten editor, entrada, árbol y resultados.

## Alcance inicial de `.g4`

La base admite gramáticas combinadas con encabezado `grammar Nombre;`.

- El archivo debe llamarse `Nombre.g4`.
- La primera regla se sugiere como inicio, pero el usuario puede elegir otra.
- El documento de entrada se procesa completo.
- Si quedan tokens después de la regla inicial, se reporta error.
- Línea y columna públicas comienzan en 1.
- Java se usa solo para generar el parser.
- La salida se reutiliza mientras la gramática no cambie.

Quedan fuera del mínimo, salvo que el profesor los exija:

- `lexer grammar` y `parser grammar` separados;
- imports de varias gramáticas;
- configuración de canales o modos desde la GUI;
- acciones Python provenientes de gramáticas no confiables;
- visualización de la ATN interna de ANTLR.

## Árbol objetivo y propietarios

```text
src/
├── antlr_mode/
│   ├── __init__.py                         [Dulce]
│   ├── grammar_info.py                     [Dulce]
│   └── runner.py                           [Dulce]
├── lexer/                                  [Base estable; no reescribir]
├── parser/
│   ├── parse_tree.py                       [Contrato común; Dulce]
│   └── ...                                 [Base YAPar; no reescribir]
├── semantic/
│   ├── __init__.py                         [Nadissa]
│   ├── diagnostics.py                      [Nadissa]
│   ├── types.py                            [Daniel]
│   ├── values.py                           [Daniel]
│   ├── expression_actions.py               [Daniel]
│   ├── symbol_table.py                     [Nadissa]
│   ├── profile.py                          [Nadissa]
│   └── evaluator.py                        [Nadissa]
└── gui/
    ├── app.py                              [Nelson]
    └── antlr_results.py                    [Nelson; solo si es necesario]

semantic_profiles/
└── compiscript.semantic.json               [Nelson coordina; todos revisan]

tests/
├── antlr_mode/
│   ├── fixtures/MiniCalc.g4
│   ├── test_grammar_info.py                [Dulce]
│   └── test_runner.py                      [Dulce]
└── semantic/
    ├── fixtures/                           [Cada responsable]
    ├── test_types.py                       [Daniel]
    ├── test_expressions.py                 [Daniel]
    ├── test_symbol_table.py                [Nadissa]
    ├── test_profile.py                     [Nadissa]
    └── test_end_to_end.py                  [Nelson]
```

Un archivo tiene un propietario principal. Los cambios externos requieren su
revisión y no deben incluir reformateos ajenos.

# Contratos compartidos

## `GrammarInfo`

Archivo: `src/antlr_mode/grammar_info.py`

| Campo | Tipo | Significado |
|---|---|---|
| `path` | `Path` | Ruta absoluta del `.g4`. |
| `name` | `str` | Nombre declarado por la gramática. |
| `kind` | `combined`, `lexer` o `parser` | Forma de la gramática. |
| `parser_rules` | `tuple[str, ...]` | Reglas disponibles en orden. |
| `default_start_rule` | propiedad | Primera regla sintáctica. |

Funciones públicas:

- `parse_g4_info(source, path="<memory>") -> GrammarInfo`;
- `inspect_g4(path) -> GrammarInfo`.

Estas funciones inspeccionan; no ejecutan Java ni generan archivos.

## Resultado ANTLR

Archivo: `src/antlr_mode/runner.py`

`AntlrDiagnostic`:

- `stage`: `LEXER` o `PARSER`;
- `line` y `column` basadas en 1;
- `message`;
- `severity`.

`AntlrToken`:

- `token_type`;
- `text`;
- `line`;
- `column`.

`AntlrAnalysisResult`:

- `grammar: GrammarInfo`;
- `start_rule`;
- `tree: ParseTreeNode | None`;
- `diagnostics`;
- `tokens`;
- `generated_directory`;
- propiedad `accepted`.

API pública:

```text
analyze_with_g4(grammar_path, source, start_rule=None)
    -> AntlrAnalysisResult
```

La GUI y las pruebas no llaman helpers privados de generación.

## Árbol común

Archivo: `src/parser/parse_tree.py`

| Campo | Uso |
|---|---|
| `symbol` | Etiqueta visible. |
| `children` | Hijos en orden fuente. |
| `rule_name` | Regla de parser. |
| `alternative` | Alternativa etiquetada. |
| `token_type` | Tipo de terminal. |
| `text` | Lexema. |
| `line`, `column` | Inicio basado en 1. |
| `end_line`, `end_column` | Fin del intervalo. |

YAPar puede continuar usando `ParseTreeNode(symbol, children)`; los campos
nuevos son opcionales.

## Diagnósticos semánticos propuestos

Archivo futuro: `src/semantic/diagnostics.py`

| Elemento | Contrato |
|---|---|
| `DiagnosticSeverity` | `ERROR`, `WARNING` |
| `DiagnosticCategory` | tipo, scope, función, control, clase, arreglo y general |
| `SourceLocation` | inicio, final y archivo opcional |
| `Diagnostic` | categoría, severidad, mensaje y ubicación |
| `DiagnosticBag.add(...)` | agrega sin lanzar ni imprimir |
| `DiagnosticBag.extend(...)` | combina resultados |
| `DiagnosticBag.has_errors` | indica si existen errores |

# Semántica sin modificar Python por gramática

Una gramática libre de contexto define sintaxis, pero no permite deducir por sí
sola reglas como “la suma exige números” o “un bloque crea scope”. Para mantener
el requisito de cargar otra gramática sin cambiar código, esas reglas deben
llegar como datos.

Se propone:

```text
semantic_profiles/<lenguaje>.semantic.json
```

El perfil asocia regla o alternativa con una acción genérica registrada y
selectores de hijos. Acciones posibles:

- declarar símbolo;
- abrir o cerrar scope;
- resolver identificador;
- producir tipo literal;
- comprobar operador o asignación;
- comprobar llamada, condición o retorno;
- declarar o consultar miembros.

Está prohibido usar `eval`, `exec` o imports indicados por el perfil. Si el
profesor exige acciones dentro del `.g4`, se agrega un adaptador hacia el mismo
motor; no un Visitor Compiscript codificado a mano.

# Integrante 1 — Daniel Chet

## Objetivo

Implementar tipos y acciones de expresiones sin importar ANTLR, YAPar, Qt ni
nombres de reglas gramaticales.

## Rama y archivos

`feature/fase3-types-expressions`

```text
src/semantic/types.py
src/semantic/values.py
src/semantic/expression_actions.py
tests/semantic/test_types.py
tests/semantic/test_expressions.py
tests/semantic/fixtures/types_*.cps
```

## `types.py`

Clases:

- `Type`;
- `PrimitiveType`;
- `ArrayType(element_type)`;
- `FunctionType(parameter_types, return_type)`;
- `ClassType(name, superclass)`;
- `ErrorType`;
- `UnknownType`.

Singletons:

`INTEGER`, `FLOAT`, `STRING`, `BOOLEAN`, `NULL`, `VOID`, `ERROR`
y `UNKNOWN`.

Funciones:

| Función | Responsabilidad |
|---|---|
| `type_from_name(name, array_depth=0, class_lookup=None)` | Resuelve anotación. |
| `common_type(types)` | Encuentra tipo común. |
| `is_numeric(type)` | Detecta números. |
| `is_boolean(type)` | Detecta booleano. |

## `values.py`

`SemanticValue` contiene tipo, valor constante opcional, asignabilidad,
mutabilidad, símbolo opcional y ubicación. Nunca contiene contextos ANTLR.

## `expression_actions.py`

`ExpressionActions` expone:

| Método | Responsabilidad |
|---|---|
| `literal(kind, text, location)` | Tipo y valor literal. |
| `unary(operator, operand, location)` | Operación unaria. |
| `binary(operator, left, right, location)` | Operación binaria. |
| `assignment(target, value, location)` | Mutabilidad y tipo. |
| `ternary(condition, true_value, false_value, location)` | Tipo común. |
| `array_literal(elements, location)` | Arreglo homogéneo. |
| `index(container, index, location)` | Tipo del elemento. |

## Pruebas y terminado

Debe cubrir compatibilidad, operadores, constantes, ternario, listas e índices,
incluyendo la misma acción invocada desde árboles con nombres diferentes.

Termina cuando no existe ningún `visit...` ni import de `antlr4` en sus
archivos.

# Integrante 2 — Dulce Ambrosio

## Objetivo

Mantener el frontend ANTLR genérico y el árbol común sin alterar YAPar.

## Rama y archivos

`feature/fase3-antlr-frontend`

```text
src/antlr_mode/__init__.py
src/antlr_mode/grammar_info.py
src/antlr_mode/runner.py
src/parser/parse_tree.py
tests/antlr_mode/
```

## Responsabilidades

- revisar comentarios, literales y reglas compactas;
- mantener la misma versión de generador y runtime;
- asegurar errores claros si Java o red faltan;
- conservar la caché por hash;
- evitar colisiones de módulos;
- recolectar errores de Lexer y Parser;
- comprobar consumo completo;
- conservar regla, alternativa, token y posiciones;
- documentar gramáticas combinadas.

APIs que no debe romper:

- `inspect_g4(path)`;
- `analyze_with_g4(path, source, start_rule)`;
- constructor compatible de `ParseTreeNode`;
- propiedad `AntlrAnalysisResult.accepted`.

Pruebas mínimas:

- Compiscript y MiniCalc;
- gramática inválida;
- nombre incorrecto;
- regla inicial inexistente;
- token inválido;
- entrada restante;
- reutilización de caché;
- coordenadas basadas en 1.

Termina cuando dos gramáticas diferentes funcionan sin cambiar `runner.py` y
las regresiones YAPar pasan.

# Integrante 3 — Nadissa Vela

## Objetivo

Implementar tabla de símbolos, perfiles y evaluador semántico genérico.

## Rama y archivos

`feature/fase3-semantic-engine`

```text
src/semantic/__init__.py
src/semantic/diagnostics.py
src/semantic/symbol_table.py
src/semantic/profile.py
src/semantic/evaluator.py
tests/semantic/test_symbol_table.py
tests/semantic/test_profile.py
tests/semantic/test_evaluator.py
```

## `symbol_table.py`

`ScopeKind`: global, función, clase y bloque.

`SymbolKind`: variable, constante, parámetro, función, clase, campo y método.

`Scope`:

- `declare(symbol)`;
- `resolve_local(name)`;
- `resolve(name)`.

`SymbolTable`:

- `enter_scope(kind, name, location)`;
- `exit_scope()`;
- `declare(symbol)`;
- `resolve(name)`;
- `iter_scopes()`.

Los scopes cerrados se conservan para mostrarlos en el IDE.

## `profile.py`

Clases: `SemanticProfile`, `RuleBinding`, `ActionInvocation`,
`ChildSelector` y `ProfileError`.

Funciones:

| Función | Responsabilidad |
|---|---|
| `load_profile(path)` | Lee y valida JSON. |
| `validate_profile(profile, grammar_info)` | Detecta reglas inexistentes. |
| `resolve_binding(node, profile)` | Prefiere alternativa y luego regla. |

## `evaluator.py`

`SemanticContext` conserva diagnósticos, tabla, tipos y pilas de función,
clase y loop.

`ActionRegistry` expone `register(name, handler)` y `resolve(name)`.

`SemanticEvaluator` expone:

- `analyze(tree, profile)`;
- `visit(node)`;
- `visit_children(node)`;
- `select(node, selector)`;
- `invoke(action, node)`.

Debe rechazar perfiles o acciones desconocidas y nunca usar `eval`.

Pruebas: scopes, redeclaración, shadowing, perfil inválido, prioridad de
alternativa, orden de recorrido y restauración de contexto después de errores.

Termina cuando árboles con nombres distintos se analizan usando perfiles
distintos sin cambiar Python.

# Integrante 4 — Nelson Escalante

## Objetivo

Conservar una sola aplicación, presentar ambos motores e integrar semántica y
pruebas end-to-end.

## Rama y archivos

`feature/fase3-ide-integration`

```text
src/gui/app.py
src/gui/antlr_results.py
semantic_profiles/compiscript.semantic.json
tests/semantic/test_end_to_end.py
README.md
docs/phase3/
```

## Base disponible en `app.py`

- `AntlrAnalysisWorker`;
- botones **Open G4**, **Mode** y **Start**;
- slot G4;
- `_open_g4()`;
- `_load_g4_rules(path)`;
- `_set_mode(mode)`;
- `_on_mode_changed()`;
- `_run_antlr_analysis()`;
- `_render_antlr_bundle(bundle)`.

Nelson extrae `antlr_results.py` solo si `app.py` crece demasiado; no
reescribe la interfaz YAPar.

## Requisitos de interfaz

- abrir y editar `.g4`;
- actualizar reglas al guardar;
- cambiar al modo correspondiente;
- usar la entrada completa en ANTLR;
- deshabilitar Analyze mientras trabaja;
- distinguir errores de generación y del programa;
- mostrar tokens, árbol y todos los diagnósticos;
- explicar por qué LR y Steps no aplican a ANTLR;
- conservar temas;
- volver a YAPar sin reiniciar.

## Perfil y pruebas

Nelson coordina el perfil Compiscript. Daniel revisa tipos y expresiones,
Nadissa scopes/control y Dulce nombres reales de reglas.

Pruebas end-to-end:

- Compiscript con inicio `program`;
- MiniCalc con inicio `root`;
- ambas consecutivamente;
- regreso a YAPar;
- entrada válida e inválida;
- perfil incompatible;
- tabla de símbolos visible;
- Graphviz o Java ausentes con mensaje claro.

Termina cuando una sola ventana ejecuta ambos modos y conserva las regresiones.

# Orden de integración

## Paso 1 — Base multimodo

Ya disponible: inspección, generación dinámica, caché, árbol común, selector de
modo/regla, tokens, árbol, errores y pruebas con dos gramáticas.

Dulce y Nelson revisan esta base antes de añadir semántica.

## Paso 2 — Contratos semánticos

1. Nadissa crea diagnósticos, símbolos y esquema de perfil.
2. Daniel crea tipos y valores.
3. Los cuatro congelan firmas.
4. Se crea un perfil mínimo para declaraciones y literales.

## Paso 3 — Motor

1. Nadissa implementa evaluator y registro.
2. Daniel registra acciones de expresiones.
3. Dulce verifica metadatos del árbol.
4. Nelson presenta diagnósticos y scopes.

## Paso 4 — Cobertura Compiscript

Orden: declaraciones, tipos, asignaciones, funciones, control, arreglos, clases
y caso integral.

## Paso 5 — Generalidad y regresión

- Compiscript;
- MiniCalc sin cambios Python;
- una tercera gramática pequeña;
- 75 entradas válidas anteriores;
- 8 entradas negativas;
- prueba manual del IDE;
- comprobar que `output/antlr/` no aparece en Git.

# Reglas para evitar conflictos

- Dulce es propietaria de `src/antlr_mode/`.
- Nelson es propietario de `src/gui/app.py`.
- Nadissa crea primero los contratos comunes de `src/semantic/`.
- Daniel no duplica diagnósticos ni tabla.
- Nadie versiona archivos generados.
- Nadie cambia contratos públicos dentro de un PR de funcionalidad.
- Cada PR incluye caso exitoso y fallido.
- Cada fixture indica gramática, regla inicial y resultado esperado.

# Checklist de Pull Request

- [ ] No codifica `Compiscript` dentro del motor.
- [ ] No importa clases generadas desde `src/semantic/`.
- [ ] No cambia fases 1 y 2 sin necesidad.
- [ ] No agrega contenido de `output/`.
- [ ] Incluye pruebas unitarias y caso de error.
- [ ] Conserva coordenadas basadas en 1.
- [ ] Mantiene trabajo pesado fuera del hilo Qt.
- [ ] Ejecuta `python -m pytest tests/antlr_mode -q`.
- [ ] Ejecuta regresiones YAPar.
- [ ] Actualiza documentación si cambia un contrato.
- [ ] Recibe revisión de otro integrante.

# Definición global de terminado

La fase está terminada cuando:

- YALex + YAPar conserva sus resultados;
- ANTLR carga una gramática combinada desde el IDE;
- otra gramática no requiere cambiar Python;
- se puede elegir regla inicial;
- se distinguen errores de generación, Lexer y Parser;
- el árbol conserva metadatos semánticos;
- las reglas semánticas se cargan como perfil o mecanismo acordado;
- los scopes requeridos quedan disponibles;
- se reportan múltiples diagnósticos;
- Compiscript y otra gramática pasan end-to-end;
- ningún generado aparece en Git;
- los cuatro integrantes tienen commits propios y revisados.


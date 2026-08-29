# Guía detallada de implementación por bloques — Fase 3

## Objetivo

El proyecto conserva el generador YALex + YAPar de las fases 1 y 2 y permite
generar el frontend de Compiscript desde una gramática ANTLR `.g4`. La Fase 3
agrega un motor semántico configurable y un IDE donde el usuario abre, escribe,
guarda y compila archivos fuente `.cps`.

`Compiscript.g4` es una entrada de ejemplo y una prueba de aceptación, no una
dependencia del sistema ni necesariamente la gramática oficial definitiva.

## Forma de trabajo obligatoria

El trabajo no se desarrolla en paralelo. Se ejecutan cuatro bloques cerrados:

```text
Base aceptada
    ↓
Daniel termina y entrega
    ↓
Nadissa termina y entrega
    ↓
Dulce termina y entrega
    ↓
Nelson termina y prepara la entrega final
```

Cada bloque cumple estas reglas:

1. comienza desde la rama donde ya se integró el bloque anterior;
2. solo usa contratos de la base o de bloques terminados;
3. incluye implementación, pruebas y documentación de sus APIs;
4. corrige sus fallos antes de entregarse;
5. congela sus APIs públicas al ser aceptado;
6. no deja tareas para que su autor regrese al final.

Una revisión de Pull Request puede hacerla cualquier integrante. Revisar no
significa volver a desarrollar el bloque.

## Invariantes del producto

- El modo **YALex + YAPar** conserva `.yal`, `.yapar`, LR(0), SLR, LALR, LL(1),
  Steps, árboles y resultados anteriores.
- El modo **ANTLR (.g4)** recibe gramática, regla inicial, perfil semántico y
  entrada desde el IDE.
- El archivo fuente del producto evaluado usa extensión `.cps`.
- ANTLR genera Lexer y Parser Python desde el `.g4`; no se versionan generados.
- Un `ParseTreeListener` recorrido mediante `ParseTreeWalker`, o un Visitor
  equivalente, aplica las acciones semánticas sobre el árbol de ANTLR.
- Los generados se guardan en `output/antlr/` y nunca se agregan a Git.
- Ningún módulo semántico importa clases generadas para Compiscript.
- El árbol común conserva regla, alternativa, token y ubicación.
- Una segunda gramática debe funcionar sin cambiar el código Python del motor.
- Los perfiles solo contienen datos; no ejecutan `eval`, `exec` ni imports.
- Descarga, generación, análisis y renderizado trabajan fuera del hilo de Qt.
- El árbol se presenta visualmente mediante nodos y aristas; un `repr` o texto
  plano aislado no es la evidencia principal de evaluación.
- Un `.cps` se acepta solo si no tiene errores léxicos, sintácticos o semánticos.

## Estado de la base antes del bloque 1

| Capacidad | Estado requerido |
|---|---|
| YALex + YAPar y sus regresiones | Implementado y estable |
| Inspección de gramáticas `.g4` | Implementado |
| Selección de regla inicial | Implementado |
| Generación y caché de ANTLR | Implementado |
| Carga dinámica de Lexer y Parser | Implementado |
| Errores léxicos y sintácticos | Implementado |
| Conversión a `ParseTreeNode` | Implementado |
| Tokens, árbol y diagnósticos en GUI | Implementado |
| Pruebas sintácticas Compiscript/MiniCalc | Implementado |
| Diagnósticos y tipos semánticos | Pendiente: Daniel |
| Motor semántico y tabla de símbolos | Pendiente: Nadissa |
| Adaptador y generalidad semántica | Pendiente: Dulce |
| Listener/Visitor semántico sobre el árbol ANTLR | Pendiente: Dulce |
| Perfil Compiscript, flujo `.cps` e IDE semántico | Pendiente: Nelson |

La base multimodo es una precondición. No se distribuye como pequeñas tareas
que reaparezcan entre los cuatro bloques.

## Flujo técnico final

```text
.g4 + archivo .cps + regla inicial
            │
            v
     frontend ANTLR genérico
            │
            v
 AntlrAnalysisResult + ParseTreeNode
            │
            ├──────────── perfil JSON
            │                  │
            v                  v
          adaptador semántico
            │
            v
 ParseTreeWalker + SemanticTreeListener
            │
            v
     SemanticEvaluator
       ├── tipos y valores
       ├── acciones genéricas
       ├── scopes y símbolos
       └── diagnósticos
            │
            v
 SemanticAnalysisResult
            │
            v
             IDE
```

## Propiedad final de archivos

```text
src/
├── antlr_mode/                                  [Dulce]
│   ├── __init__.py
│   ├── grammar_info.py
│   └── runner.py
├── parser/
│   ├── parse_tree.py                            [Dulce; contrato congelado]
│   └── ...                                      [Base YAPar; no reescribir]
├── semantic/
│   ├── __init__.py                              [Daniel; sin reexportaciones]
│   ├── diagnostics.py                           [Daniel]
│   ├── types.py                                 [Daniel]
│   ├── values.py                                [Daniel]
│   ├── expression_actions.py                    [Daniel]
│   ├── symbol_table.py                          [Nadissa]
│   ├── profile.py                               [Nadissa]
│   ├── action_registry.py                       [Nadissa]
│   ├── results.py                               [Nadissa]
│   ├── evaluator.py                             [Nadissa]
│   ├── actions/                                 [Nadissa]
│   ├── antlr_listener.py                        [Dulce]
│   └── antlr_adapter.py                         [Dulce]
└── gui/
    ├── app.py                                   [Nelson]
    ├── antlr_results.py                         [Nelson; si se necesita]
    ├── semantic_results.py                      [Nelson]
    └── parse_tree_view.py                       [Nelson]

semantic_profiles/
├── minicalc.semantic.json                       [Dulce]
└── compiscript.semantic.json                    [Nelson]

tests/
├── antlr_mode/                                  [Dulce]
└── semantic/
    ├── test_diagnostics.py                      [Daniel]
    ├── test_types.py                            [Daniel]
    ├── test_expressions.py                      [Daniel]
    ├── test_symbol_table.py                     [Nadissa]
    ├── test_profile.py                          [Nadissa]
    ├── test_evaluator.py                        [Nadissa]
    ├── test_statement_actions.py                [Nadissa]
    ├── test_functions.py                        [Nadissa]
    ├── test_control_flow.py                     [Nadissa]
    ├── test_classes.py                          [Nadissa]
    ├── test_general_semantics.py                [Nadissa]
    ├── test_antlr_adapter.py                    [Dulce]
    ├── test_antlr_listener.py                   [Dulce]
    ├── test_generic_grammar.py                  [Dulce]
    └── test_end_to_end.py                       [Nelson]
└── gui/
    └── test_cps_workflow.py                     [Nelson]
```

La cobertura exacta y los IDs obligatorios se encuentran en
[`MATRIZ_CUMPLIMIENTO.md`](MATRIZ_CUMPLIMIENTO.md). Un nombre general como
`test_evaluator.py` no es evidencia suficiente si no puede localizarse el caso
exitoso y fallido de cada regla del PDF.

`src/semantic/__init__.py` no reexporta las clases de otros módulos. Así
Nadissa y Dulce pueden agregar archivos sin modificar uno propiedad de Daniel.

# Contratos de la base congelada

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

## Resultado ANTLR

Archivo: `src/antlr_mode/runner.py`

`AntlrAnalysisResult` conserva:

- `grammar`;
- `start_rule`;
- `tree: ParseTreeNode | None`;
- `native_tree` o una sesión equivalente para el recorrido ANTLR;
- nombres de reglas necesarios para identificar cada contexto sin importar
  clases generadas concretas;
- `diagnostics`;
- `tokens`;
- `generated_directory`;
- propiedad `accepted`.

API pública:

```text
analyze_with_g4(grammar_path, source, start_rule=None)
    -> AntlrAnalysisResult
```

Los bloques posteriores no llaman helpers privados de generación.

El acceso al árbol nativo se expone únicamente para el adaptador semántico. La
GUI y el motor genérico consumen los resultados públicos, no clases generadas.

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

YAPar puede continuar usando `ParseTreeNode(symbol, children)` porque los
metadatos nuevos son opcionales.

# Bloque 1 — Daniel Chet

## Objetivo y entrada

Daniel recibe únicamente Python, la especificación semántica confirmada y los
contratos anteriores como referencia. Su código no necesita árboles, gramáticas,
Java, ANTLR, perfiles ni Qt.

Rama:

```text
feature/fase3-01-semantic-core
```

Archivos:

```text
src/semantic/__init__.py
src/semantic/diagnostics.py
src/semantic/types.py
src/semantic/values.py
src/semantic/expression_actions.py
tests/semantic/test_diagnostics.py
tests/semantic/test_types.py
tests/semantic/test_expressions.py
tests/semantic/fixtures/types_*.cps
```

## `diagnostics.py`

Clases y enumeraciones:

- `DiagnosticSeverity`: `ERROR` y `WARNING`;
- `DiagnosticCategory`: tipo, scope, función, control, clase, arreglo y general;
- `SourceLocation`: inicio, final y archivo opcional;
- `Diagnostic`: categoría, severidad, mensaje y ubicación;
- `DiagnosticBag`: colección acumulable.

API pública de `DiagnosticBag`:

| Método o propiedad | Responsabilidad |
|---|---|
| `add(category, message, location, severity=ERROR)` | Agrega sin lanzar ni imprimir. |
| `extend(diagnostics)` | Combina diagnósticos conservando el orden. |
| `items` | Devuelve una vista inmutable. |
| `has_errors` | Indica si existe al menos un error. |

## `types.py`

Clases:

- `Type`;
- `PrimitiveType`;
- `ArrayType(element_type)`;
- `FunctionType(parameter_types, return_type)`;
- `ClassType(name, superclass=None)`;
- `ErrorType`;
- `UnknownType`.

Singletons:

`INTEGER`, `FLOAT`, `STRING`, `BOOLEAN`, `NULL`, `VOID`, `ERROR` y `UNKNOWN`.

Funciones públicas:

| Función | Responsabilidad |
|---|---|
| `type_from_name(name, array_depth=0, class_lookup=None)` | Resuelve una anotación. |
| `is_assignable(source, target)` | Comprueba compatibilidad de asignación. |
| `common_type(types)` | Obtiene un tipo común o `ERROR`. |
| `is_numeric(type_)` | Reconoce `integer` y `float`. |
| `is_boolean(type_)` | Reconoce `boolean`. |

## `values.py`

`SemanticValue` contiene:

- `type`;
- valor constante opcional;
- `assignable`;
- `mutable`;
- referencia opcional a símbolo mediante un protocolo neutral;
- ubicación.

Nunca contiene contextos ANTLR, nodos Qt o nombres de reglas gramaticales.

## `expression_actions.py`

`ExpressionActions` recibe un `DiagnosticBag` en su constructor y expone:

| Método | Responsabilidad |
|---|---|
| `literal(kind, text, location)` | Produce tipo y valor literal. |
| `unary(operator, operand, location)` | Valida una operación unaria. |
| `binary(operator, left, right, location)` | Valida una operación binaria. |
| `assignment(target, value, location)` | Valida mutabilidad y tipo. |
| `ternary(condition, true_value, false_value, location)` | Calcula tipo común. |
| `array_literal(elements, location)` | Valida un arreglo homogéneo. |
| `index(container, index, location)` | Produce el tipo del elemento. |

## Pruebas del bloque 1

Debe cubrir:

- igualdad, representación y compatibilidad de tipos;
- promoción `integer`/`float`;
- propagación de `ERROR` y `UNKNOWN`;
- operadores válidos e inválidos;
- asignación a constantes;
- ternarios, arreglos e índices;
- acumulación de más de un diagnóstico.

Además debe implementar los casos `TYP-01` a `TYP-04`, `TYP-06`, `LST-01`,
`LST-02` y `GEN-02` de la matriz de cumplimiento. Cada ID conserva un caso
exitoso y uno fallido.

Las pruebas llaman directamente a las clases y acciones. No construyen
`ParseTreeNode`.

## Puerta Daniel → Nadissa

El bloque termina cuando:

- pasan todas sus pruebas unitarias;
- no existen imports de `antlr4`, `src.antlr_mode`, `src.parser` o `PyQt6`;
- las APIs anteriores están documentadas y no quedan `TODO` funcionales;
- Daniel integra su rama y no necesita regresar para implementar otro bloque.

# Bloque 2 — Nadissa Vela

## Objetivo y entrada

Nadissa recibe el núcleo semántico terminado de Daniel y el contrato estable de
`ParseTreeNode`. Entrega un motor capaz de analizar árboles manuales, sin
depender todavía de ANTLR, Java o GUI.

Rama:

```text
feature/fase3-02-semantic-engine
```

Archivos:

```text
src/semantic/symbol_table.py
src/semantic/profile.py
src/semantic/action_registry.py
src/semantic/results.py
src/semantic/evaluator.py
src/semantic/actions/__init__.py
src/semantic/actions/declarations.py
src/semantic/actions/control_flow.py
src/semantic/actions/callables.py
src/semantic/actions/classes.py
tests/semantic/test_symbol_table.py
tests/semantic/test_profile.py
tests/semantic/test_evaluator.py
tests/semantic/test_statement_actions.py
tests/semantic/test_functions.py
tests/semantic/test_control_flow.py
tests/semantic/test_classes.py
tests/semantic/test_general_semantics.py
```

## `symbol_table.py`

Enumeraciones:

- `ScopeKind`: global, función, clase y bloque;
- `SymbolKind`: variable, constante, parámetro, función, clase, campo y método.

`Symbol` conserva nombre, clase, tipo, mutabilidad, ubicación y metadatos
necesarios para funciones o miembros.

`Scope` expone:

- `declare(symbol)`;
- `resolve_local(name)`;
- `resolve(name)`;
- `symbols` como vista inmutable.

`SymbolTable` expone:

- `enter_scope(kind, name, location)`;
- `exit_scope()`;
- `declare(symbol)`;
- `resolve(name)`;
- `iter_scopes()`.

Los scopes cerrados se conservan para mostrarlos posteriormente en el IDE.

## `profile.py`

Clases:

- `SemanticProfile`;
- `RuleBinding`;
- `ActionInvocation`;
- `ChildSelector`;
- `ProfileError`.

Funciones:

| Función | Responsabilidad |
|---|---|
| `load_profile(path)` | Lee JSON y valida su esquema. |
| `validate_profile(profile, available_rules)` | Detecta reglas declaradas que no existen. |
| `resolve_binding(node, profile)` | Prefiere alternativa y luego regla. |

Los selectores solo pueden identificar hijos, tokens, texto o posiciones. El
perfil no contiene expresiones Python. `available_rules` es una colección de
nombres; `profile.py` no importa `GrammarInfo` ni ningún módulo ANTLR.

## `action_registry.py`

`ActionRegistry` expone:

- `register(name, handler)`;
- `resolve(name)`;
- `names` como colección inmutable.

Registra las acciones de expresiones de Daniel y las acciones de sentencias de
Nadissa con nombres estables. Una acción desconocida produce `ProfileError`.

## `results.py`

`SemanticAnalysisResult` contiene:

- diagnósticos inmutables;
- tabla de símbolos completa;
- valor semántico final opcional;
- propiedad `accepted`;
- estadísticas opcionales de reglas y acciones ejecutadas.

## `evaluator.py`

`SemanticContext` conserva:

- `DiagnosticBag`;
- `SymbolTable`;
- `ExpressionActions`;
- pilas de función, clase y ciclo;
- resultados temporales por nodo.

`SemanticEvaluator` expone:

- `analyze(tree, profile) -> SemanticAnalysisResult`;
- `visit(node)`;
- `visit_children(node)`;
- `select(node, selector)`;
- `invoke(action, node)`.

Debe restaurar scopes y pilas aunque una acción reporte errores.

## Acciones de sentencias

Los módulos bajo `src/semantic/actions/` implementan acciones genéricas para:

- declarar variables, constantes, parámetros, funciones y clases;
- abrir y cerrar scopes;
- resolver identificadores;
- validar llamadas, argumentos y retornos;
- permitir recursión y capturar entornos para funciones anidadas y closures;
- validar condiciones, `break` y `continue`;
- detectar instrucciones inalcanzables después de `return`, `break` u otra
  transferencia definitiva;
- registrar campos, métodos, constructores y `this`.

Ninguna acción menciona `Compiscript`, `program`, `statement` u otro nombre de
regla. El perfil posterior decide dónde se invoca cada acción.

## Pruebas del bloque 2

Debe cubrir:

- scopes, redeclaración, shadowing y resolución;
- preservación de scopes cerrados;
- perfil válido, JSON inválido, acción desconocida y selector inválido;
- prioridad de alternativa sobre regla;
- orden de recorrido;
- declaraciones, funciones, control y clases;
- recursión, closures y redeclaración de funciones;
- una condición válida e inválida para `if`, `while`, `do-while`, `for` y
  `switch`;
- `break`, `continue` y `return` dentro y fuera de su contexto permitido;
- atributos, métodos, constructores y `this` válidos e inválidos;
- código muerto y duplicación de variables o parámetros;
- restauración de contexto después de errores;
- múltiples diagnósticos en un mismo árbol.

Debe cubrir todos los IDs `TYP-05`, `SCP-*`, `FUN-*`, `CTL-*`, `CLS-*`,
`GEN-01` y `GEN-03` definidos en `MATRIZ_CUMPLIMIENTO.md`.

Las pruebas crean `ParseTreeNode` manualmente. No cargan `.g4` ni abren el IDE.

## Puerta Nadissa → Dulce

El bloque termina cuando:

- un árbol manual produce tipos, diagnósticos y tabla de símbolos;
- un segundo perfil con nombres de reglas diferentes usa las mismas acciones;
- no existen imports de `antlr4`, `src.antlr_mode` o `PyQt6`;
- no se usa `eval`, `exec` ni carga dinámica indicada por JSON;
- Nadissa integra su rama y no necesita regresar durante los bloques 3 y 4.

# Bloque 3 — Dulce Ambrosio

## Objetivo y entrada

Dulce recibe el frontend ANTLR de la base y el motor semántico terminado. Su
bloque conecta ambas piezas y demuestra que el diseño funciona con una
gramática distinta de Compiscript.

Rama:

```text
feature/fase3-03-antlr-semantic
```

Archivos:

```text
src/antlr_mode/__init__.py
src/antlr_mode/grammar_info.py
src/antlr_mode/runner.py
src/parser/parse_tree.py
src/semantic/antlr_listener.py
src/semantic/antlr_adapter.py
semantic_profiles/minicalc.semantic.json
tests/antlr_mode/
tests/semantic/test_antlr_adapter.py
tests/semantic/test_antlr_listener.py
tests/semantic/test_generic_grammar.py
```

## Frontend ANTLR

Debe conservar estas APIs:

- `inspect_g4(path)`;
- `analyze_with_g4(path, source, start_rule=None)`;
- constructor compatible de `ParseTreeNode`;
- propiedad `AntlrAnalysisResult.accepted`.

Responsabilidades:

- versión compatible entre generador y runtime;
- errores claros si Java, red o JAR faltan;
- caché por hash;
- aislamiento de módulos generados;
- errores de Lexer y Parser;
- consumo completo de la entrada;
- metadatos de regla, alternativa, token y posición.

## `antlr_listener.py`

`SemanticTreeListener` hereda de `antlr4.ParseTreeListener` y se ejecuta con
`antlr4.ParseTreeWalker`. No hereda de un Listener generado para Compiscript ni
importa clases concretas de una gramática.

API y comportamiento:

- `enterEveryRule(ctx)` identifica regla y alternativa y abre el contexto
  semántico necesario;
- `visitTerminal(node)` conserva tipo, texto y posición del token;
- `visitErrorNode(node)` agrega diagnóstico cuando corresponda;
- `exitEveryRule(ctx)` resuelve el binding del perfil e invoca la acción
  registrada;
- `result` produce el `SemanticAnalysisResult` final.

El Listener recibe los nombres de reglas de la sesión ANTLR y el perfil como
datos. Por eso puede recorrer otra gramática sin editar Python.

## `antlr_adapter.py`

Clases propuestas:

- `SemanticRunRequest`: gramática, texto fuente, ruta `.cps` opcional, regla
  inicial y perfil;
- `SemanticRunResult`: resultado sintáctico y resultado semántico opcional;
- `SemanticAdapterError`: error de configuración o incompatibilidad.

API pública:

```text
analyze_semantics_with_g4(
    grammar_path,
    source,
    profile_path,
    start_rule=None,
    source_path=None,
) -> SemanticRunResult
```

Orden interno:

1. inspeccionar y analizar la gramática;
2. devolver únicamente el resultado sintáctico si este tiene errores;
3. cargar el perfil y validarlo contra `grammar.parser_rules`;
4. crear `SemanticTreeListener` con el evaluador y el perfil;
5. recorrer el árbol nativo mediante
   `ParseTreeWalker.DEFAULT.walk(listener, native_tree)`;
6. devolver ambos resultados sin imprimir ni interactuar con Qt.

`SemanticRunResult.accepted` es verdadero únicamente cuando los resultados
léxico, sintáctico y semántico están aceptados. `source_path` se propaga a las
ubicaciones para que el IDE pueda identificar el `.cps` de cada diagnóstico.

No es suficiente recorrer solamente una copia del árbol con recursión Python:
la prueba `ANT-02` debe demostrar el uso real del Listener/Visitor de ANTLR.

## Perfil MiniCalc

`semantic_profiles/minicalc.semantic.json` demuestra que:

- el motor no depende de los nombres de Compiscript;
- las acciones de literales y operadores son reutilizables;
- cambiar de gramática y perfil no modifica archivos Python.

Este perfil es una prueba técnica pequeña, no una segunda implementación del
motor.

## Pruebas del bloque 3

Debe cubrir:

- Compiscript y MiniCalc en el frontend sintáctico;
- gramática inválida y regla inicial inexistente;
- perfil incompatible con una gramática;
- error sintáctico que impide ejecutar semántica;
- análisis semántico exitoso y fallido de MiniCalc;
- dos gramáticas ejecutadas consecutivamente;
- coordenadas basadas en 1 y reutilización de caché.

También debe cubrir `ANT-01` a `ANT-06`. La prueba de árbol visual puede
verificar el modelo de nodos y aristas; la presentación final pertenece a
Nelson.

## Puerta Dulce → Nelson

El bloque termina cuando una llamada Python a `analyze_semantics_with_g4`:

- procesa una gramática y un perfil seleccionados en tiempo de ejecución;
- devuelve diagnósticos y símbolos sin utilizar GUI;
- funciona con MiniCalc sin cambiar el motor;
- mantiene las regresiones YAPar y ANTLR;
- queda documentada para que Nelson solo consuma la API pública.

Dulce integra su rama y no necesita regresar para construir el perfil
Compiscript ni la interfaz.

# Bloque 4 — Nelson Escalante

## Objetivo y entrada

Nelson recibe una API que ya ejecuta sintaxis y semántica desde Python. Su
bloque presenta esos resultados en el IDE, crea el perfil del lenguaje de
entrega y realiza las pruebas finales.

Rama:

```text
feature/fase3-04-ide-delivery
```

Archivos:

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

## Perfil Compiscript

Nelson construye `compiscript.semantic.json` usando exclusivamente:

- nombres reales obtenidos de la gramática seleccionada;
- acciones publicadas por `ActionRegistry`;
- selectores aceptados por `profile.py`;
- reglas semánticas confirmadas en `REGLAS_Y_DECISIONES.md`.

No necesita que Daniel, Nadissa o Dulce regresen a implementarlo. Si una regla
de la gramática de ejemplo cambia, Nelson actualiza el archivo JSON, no el motor
Python.

## Integración en el IDE

Requisitos:

- abrir y editar `.g4`;
- abrir, crear, editar y guardar archivos fuente `.cps`;
- elegir regla inicial y perfil semántico;
- ofrecer una acción visible **Compile** o **Analyze** para el `.cps` actual;
- ejecutar `analyze_semantics_with_g4` fuera del hilo principal usando todo el
  contenido del editor `.cps`;
- deshabilitar Analyze mientras trabaja;
- distinguir errores de generación, Lexer, Parser, perfil y semántica;
- mostrar tokens, árbol, diagnósticos, scopes y símbolos;
- mostrar el árbol como representación visual de nodos y aristas mediante
  Graphviz o una vista jerárquica equivalente;
- distinguir warnings y errores;
- explicar por qué LR y Steps no aplican al modo ANTLR;
- conservar temas y volver a YAPar sin reiniciar.

`semantic_results.py` se responsabiliza de transformar resultados en vistas. No
decide compatibilidad de tipos ni resolución de símbolos.

## Pruebas end-to-end

Debe cubrir:

- Compiscript con la regla inicial correspondiente;
- MiniCalc y Compiscript ejecutados consecutivamente;
- entrada válida e inválida;
- perfil incompatible;
- diagnósticos semánticos múltiples;
- tabla de símbolos visible;
- regreso al modo YAPar;
- Java o Graphviz ausentes con mensajes claros;
- regresiones de las fases 1 y 2.

Debe cubrir `IDE-01` a `IDE-08`. La prueba manual de presentación incluye abrir
un `.cps`, modificarlo, guardarlo, compilarlo y navegar por árbol, errores y
tabla de símbolos sin salir de la ventana.

## Puerta Nelson → entrega

El bloque termina cuando:

- una sola ventana ejecuta ambos modos;
- el flujo principal recibe un archivo `.cps`, no una cadena sin identidad de
  archivo;
- el perfil Compiscript cubre el alcance confirmado;
- el árbol sintáctico tiene representación visual;
- las pruebas unitarias, de integración y regresión pasan;
- `output/antlr/` no aparece en Git;
- README y documentos describen el comportamiento real;
- no quedan tareas de implementación para integrantes anteriores.

# Secuencia de ramas e integración

```text
feature/fase3-compiscript
    └── feature/fase3-01-semantic-core          [Daniel]
            └── integración aceptada
                    └── feature/fase3-02-semantic-engine     [Nadissa]
                            └── integración aceptada
                                    └── feature/fase3-03-antlr-semantic [Dulce]
                                            └── integración aceptada
                                                    └── feature/fase3-04-ide-delivery [Nelson]
```

Procedimiento por bloque:

1. actualizar la rama de integración;
2. crear la rama del bloque desde ese punto;
3. implementar únicamente los archivos asignados;
4. ejecutar pruebas propias y regresiones disponibles;
5. abrir Pull Request;
6. corregir todos los fallos antes de integrar;
7. documentar las APIs que consumirá el siguiente bloque;
8. integrar y cerrar la participación de su autor.

# Reglas que evitan dependencias hacia atrás

- Daniel no usa diagnósticos o tipos definidos por Nadissa.
- Nadissa no deja acciones semánticas pendientes para Daniel.
- Dulce no cambia contratos internos de Daniel o Nadissa.
- Nelson no solicita nuevos handlers para construir el perfil Compiscript.
- Un bloque posterior no edita archivos propiedad de un bloque cerrado.
- Si falta una capacidad, se detecta en la puerta anterior antes de comenzar el
  siguiente bloque.
- Los perfiles adaptan gramáticas; el código Python no se modifica por cada
  `.g4`.

# Checklist de cada Pull Request

- [ ] Solo modifica archivos del bloque actual.
- [ ] Incluye al menos un caso exitoso y uno fallido.
- [ ] Cada regla del PDF está asociada con un ID de
  `MATRIZ_CUMPLIMIENTO.md` y ambas pruebas son localizables.
- [ ] No codifica Compiscript dentro del motor genérico.
- [ ] No importa clases generadas desde `src/semantic/`.
- [ ] No cambia fases 1 y 2 sin necesidad.
- [ ] No agrega contenido de `output/`.
- [ ] Mantiene coordenadas basadas en 1.
- [ ] El recorrido semántico integrado usa Listener/Visitor de ANTLR.
- [ ] No deja `TODO` requerido por bloques posteriores.
- [ ] Documenta todas las APIs públicas entregadas.
- [ ] Ejecuta las pruebas de su bloque y las regresiones existentes.
- [ ] Cumple su puerta de aceptación antes de integrarse.

# Definición global de terminado

La Fase 3 termina cuando:

- YALex + YAPar conserva sus resultados;
- ANTLR carga una gramática combinada desde el IDE;
- se puede elegir gramática, regla inicial y perfil;
- el IDE abre, edita, guarda y compila `.cps`;
- cambiar de gramática no requiere cambiar Python;
- el árbol conserva metadatos semánticos y tiene representación visual;
- un Listener o Visitor de ANTLR aplica las acciones semánticas;
- se acumulan diagnósticos con ubicación;
- los scopes y símbolos quedan disponibles para el IDE;
- Compiscript y otra gramática pasan de extremo a extremo;
- ningún generado aparece en Git;
- cada integrante completó un único bloque cerrado;
- ningún integrante debe regresar para completar una tarea de implementación.

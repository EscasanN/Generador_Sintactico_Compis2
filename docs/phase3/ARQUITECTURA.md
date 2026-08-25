# Arquitectura — Fase 3

## Base estable

El repositorio conserva:

- `src/lexer/`: YALex, NFA, DFA y minimización;
- `src/parser/`: YAPar, LR(0), SLR, LALR, LL(1) y árbol;
- `src/gui/app.py`: IDE de las fases 1 y 2.

El modo ANTLR se agrega como frontend paralelo y no reemplaza esos módulos.

## Flujo multimodo

```text
                ┌── .yal + .yapar ──> motor propio YALex/YAPar ──┐
IDE + entrada ──┤                                                ├──> vistas
                └── .g4 + start rule ──> runtime ANTLR ──────────┘
                                                    │
                                                    v
                                           ParseTreeNode común
                                                    │
                                                    v
                                      motor semántico configurable
```

## `src/antlr_mode/`

### `grammar_info.py`

Inspecciona la gramática sin generar código. Produce `GrammarInfo` con ruta,
nombre, tipo y reglas de parser.

### `runner.py`

1. valida la gramática y regla inicial;
2. resuelve Java y ANTLR 4.13.2;
3. descarga el JAR en el primer uso si es necesario;
4. calcula hash de versión y contenido;
5. genera Python en `output/antlr/generated/`;
6. carga Lexer y Parser dinámicamente;
7. recolecta errores;
8. verifica consumo completo;
9. convierte el árbol al modelo común.

Los generados son caché reproducible, no código fuente del proyecto.

## Árbol común

`ParseTreeNode` mantiene compatibilidad con YAPar y agrega metadatos opcionales:

- regla;
- alternativa etiquetada;
- tipo y texto de token;
- ubicación inicial y final.

La semántica futura consume este modelo, nunca contextos ANTLR concretos.

## GUI

`MainWindow` conserva una sola aplicación. `AnalysisWorker` atiende YAPar y
`AntlrAnalysisWorker` atiende `.g4`. Ambos trabajan fuera del hilo principal.

El modo determina requisitos y renderizado:

- YAPar: vistas históricas completas;
- ANTLR: tokens, árbol y diagnósticos;
- cambiar de modo no borra archivos cargados del otro flujo.

## Semántica genérica

Una gramática solo describe sintaxis. Para evitar código diferente por lenguaje,
se propone un perfil declarativo que asocie reglas o alternativas con acciones
registradas:

```text
semantic profile + ParseTreeNode
              │
              v
SemanticEvaluator
├── TypeSystem
├── SymbolTable
├── ExpressionActions
├── acciones de función/control/clase
└── DiagnosticBag
```

El perfil no ejecuta Python arbitrario. No se permite `eval`, `exec` ni
imports configurables.

## Límites

- `src/antlr_mode/` no contiene semántica Compiscript.
- `src/semantic/` no importa ANTLR ni PyQt6.
- `src/gui/` presenta resultados, no decide tipos o scopes.
- `src/lexer/` y `src/parser/` no se reescriben para soportar `.g4`.
- `output/` no se versiona.

## Dependencias

- Java 11 o superior para ejecutar el generador.
- ANTLR Tool 4.13.2, descargado o indicado mediante `ANTLR4_JAR`.
- `antlr4-python3-runtime==4.13.2`.
- Graphviz para imágenes.
- PyQt6 para el IDE.

Generador y runtime deben compartir versión.

## Seguridad y fallos

Las gramáticas se consideran entradas proporcionadas por el curso. Aun así:

- la descarga usa la URL oficial;
- los procesos se invocan con argumentos, no mediante shell;
- la generación tiene timeout;
- los errores se muestran sin cerrar el IDE;
- las cachés se encuentran bajo una ruta ignorada;
- acciones embebidas no confiables quedan fuera del alcance.

## Generalidad verificable

La base prueba:

- `Compiscript.g4` con regla `program`;
- `MiniCalc.g4` con regla `root`.

Ambas usan la misma función `analyze_with_g4`. Esta prueba debe mantenerse para
impedir acoplamiento accidental.

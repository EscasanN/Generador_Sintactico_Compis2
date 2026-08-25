# Arquitectura propuesta — Fase 3

## Estado de la base

El repositorio ya contiene dos subsistemas funcionales:

- `src/lexer/`: procesa especificaciones YALex y construye NFA, DFA y DFA mínimo.
- `src/parser/`: procesa gramáticas YAPar y construye analizadores LR(0), SLR(1), LALR y LL(1).

Estos módulos se conservan como base y como regresión. La Fase 3 agrega un front-end específico para Compiscript; no reemplaza los analizadores existentes.

## Flujo objetivo

```text
Código .cps
    ↓
Lexer y Parser generados por ANTLR
    ↓
ParseResult (árbol + diagnósticos sintácticos)
    ↓
SemanticVisitor
    ├── sistema de tipos
    ├── tabla de símbolos
    ├── validadores por dominio
    └── recolector de diagnósticos
    ↓
AnalysisResult
    ├── árbol sintáctico
    ├── errores semánticos
    └── árbol de entornos y símbolos
    ↓
IDE Compiscript
```

## Límites de responsabilidad

### `src/compiscript/`

Contiene todo lo dependiente de la gramática y de las clases generadas por ANTLR. `parser.py` adapta ANTLR a estructuras propias y `analyzer.py` coordina el recorrido semántico.

### `src/semantic/`

Contiene estructuras y reglas que no necesitan conocer widgets de Qt ni rutas de archivos. El sistema de tipos es la única fuente de verdad para compatibilidad; no se duplicarán esas reglas en un `validator.py` genérico.

### `src/gui/`

Solo presenta resultados y coordina el trabajo en segundo plano. No debe decidir reglas semánticas.

### `tests/semantic/`

Separa fixtures `.cps` de pruebas Python. Los ejemplos se agregarán únicamente después de comprobar que son válidos para la gramática oficial.

## Contratos mínimos

```text
ParseResult
├── tree
├── lexer
├── parser
└── diagnostics: list[Diagnostic]

AnalysisResult
├── parse_result: ParseResult
├── diagnostics: list[Diagnostic]
└── symbols: SymbolTable

Diagnostic
├── category
├── message
├── line
├── column
└── severity
```

Los nombres finales pueden cambiar durante la Fase 0, pero deben acordarse antes de dividir el desarrollo.

## Código generado

- `Compiscript.g4` es la fuente.
- `src/compiscript/generated/` es la única salida.
- Los `.py` generados se versionarán para que la evaluación no dependa de tener Java instalado.
- La versión del generador ANTLR y la del runtime Python deben ser compatibles.
- Los archivos generados nunca se editan manualmente.

## Decisiones de diseño

- Los diagnósticos se acumulan para reportar varios problemas en una pasada.
- Un tipo de error centinela evita cascadas de mensajes derivados de un mismo fallo.
- Los scopes cerrados se conservan como hijos del scope raíz para visualizar la tabla completa.
- La GUI ejecuta parser, análisis y renderizado fuera del hilo principal.
- La semántica se prueba sin GUI; la interfaz se considera un consumidor de `AnalysisResult`.

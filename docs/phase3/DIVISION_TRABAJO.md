# División del trabajo — Fase 3

## Equipo

El profesor autorizó expresamente un equipo de cuatro integrantes. La distribución se organiza por capacidades completas: cada persona implementa código, pruebas y la documentación de su dominio.

| Integrante | Frente principal | Rama sugerida |
|---|---|---|
| Daniel Chet | Tipos, expresiones y listas | `feature/fase3-types-expressions` |
| Dulce Ambrosio | ANTLR, parser y coordinación del Visitor | `feature/fase3-parser` |
| Nadissa Vela | Símbolos, funciones y control de flujo | `feature/fase3-scopes-functions` |
| Nelson Escalante | Clases, IDE e integración | `feature/fase3-classes-ide` |

Los porcentajes de la rúbrica no se asignan a personas. La nota corresponde al producto integrado.

## Trabajo común inicial

Antes de separarse, todos participan en un único PR de contrato:

- confirmar la gramática oficial;
- resolver las decisiones abiertas;
- aprobar las estructuras `Diagnostic`, `ParseResult`, `AnalysisResult`, `Type`, `Symbol` y `SymbolTable`;
- acordar la ubicación de archivos generados;
- preparar un smoke test del parser.

Después de ese PR, los frentes pueden avanzar en paralelo.

## Daniel — Tipos, expresiones y listas

### Responsabilidades

- Jerarquía de tipos primitivos, arreglos, funciones, clases y tipo de error.
- Compatibilidad de asignación y comparación.
- Operaciones aritméticas, lógicas, relacionales y unarias.
- Inferencia básica en declaraciones.
- Literales de listas, homogeneidad, índices y asignación de elementos.
- Tests de tipos, expresiones y listas.

### Archivos principales

```text
src/semantic/types.py
src/semantic/expressions.py
tests/semantic/test_types.py
tests/semantic/test_arrays.py
```

### Entrega mínima

- Una regla de compatibilidad central, sin duplicarla en helpers externos.
- Casos exitosos y fallidos de cada operador y asignación.
- Un caso end-to-end aportado a `test_end_to_end.py`.

## Dulce — ANTLR, parser y coordinación del Visitor

### Responsabilidades

- Obtener y registrar la gramática oficial.
- Generar Lexer, Parser y Visitor de ANTLR.
- Implementar el adaptador `build_parse_tree` y diagnósticos sintácticos.
- Crear `SemanticVisitor` como coordinador de los módulos semánticos.
- Coordinar el orden de declaraciones necesario para recursión y referencias adelantadas, si la especificación lo permite.
- Renderizado del árbol sintáctico independiente de Qt.
- Tests del parser y recuperación de errores.

### Archivos principales

```text
src/compiscript/grammar/Compiscript.g4
src/compiscript/generated/
src/compiscript/parser.py
src/compiscript/analyzer.py
src/semantic/diagnostics.py
src/utils/visualizer.py
tests/semantic/test_parser.py
```

### Entrega mínima

- Parser reproducible y compatible con el runtime instalado.
- Múltiples errores sintácticos recolectados sin cerrar la aplicación.
- Un caso end-to-end aportado a `test_end_to_end.py`.

## Nadissa — Tabla de símbolos, funciones y control de flujo

### Responsabilidades

- Árbol de scopes global, función, clase y bloque.
- Declaración, resolución, redeclaración y shadowing.
- Parámetros, llamadas, retorno, recursión, funciones anidadas y closures.
- Condiciones, ciclos, `break`, `continue`, `return` y código muerto.
- Tests de scopes, funciones y control de flujo.

### Archivos principales

```text
src/semantic/symbol_table.py
src/semantic/functions.py
src/semantic/control_flow.py
tests/semantic/test_scopes.py
tests/semantic/test_functions.py
tests/semantic/test_control_flow.py
```

### Entrega mínima

- Scopes cerrados disponibles para inspección posterior.
- Casos de recursión, closure y declaraciones duplicadas.
- Un caso end-to-end aportado a `test_end_to_end.py`.

## Nelson — Clases, IDE e integración

### Responsabilidades

- Clases, atributos, métodos, constructores y `this`.
- Herencia únicamente si la gramática oficial y la prioridad del proyecto lo confirman.
- Pestaña de Compiscript y worker de análisis.
- Visualización de diagnósticos y tabla de símbolos.
- Pruebas de clases, integración completa y guía final de ejecución.

### Archivos principales

```text
src/semantic/classes.py
src/gui/compiscript_tab.py
src/gui/app.py
tests/semantic/test_classes.py
tests/semantic/test_end_to_end.py
README.md
docs/phase3/
```

### Entrega mínima

- El IDE abre, guarda y analiza `.cps` sin bloquear la interfaz.
- Casos de atributo inexistente, constructor inválido y uso incorrecto de `this`.
- Integración de aportes end-to-end de los cuatro integrantes.

## Reglas de colaboración

- Cada PR incluye implementación y pruebas del mismo dominio.
- Ninguna persona queda asignada únicamente a pruebas o documentación.
- Un archivo tiene un responsable principal; cambios externos requieren coordinación.
- Los PRs pequeños se integran durante el desarrollo, no al final de una cadena de dependencias.
- Cada commit pertenece a un solo integrante y describe una unidad concreta de trabajo.
- Cada PR recibe revisión de una persona distinta a su autor.

## Orden recomendado de integración

1. Contratos y parser mínimo.
2. Tipos y tabla de símbolos en paralelo.
3. Expresiones, funciones, control de flujo y clases en paralelo.
4. IDE e integración continua a medida que aparecen resultados utilizables.
5. Hardening, documentación final y ensayo de presentación.

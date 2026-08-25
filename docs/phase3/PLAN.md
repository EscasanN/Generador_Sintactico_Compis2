# Plan de implementación — Fase 3

## Objetivo

Construir un front-end de Compiscript que use ANTLR para producir el árbol sintáctico y un Visitor para:

- validar tipos, ámbitos, funciones, control de flujo, clases y listas;
- conservar una tabla de símbolos con entornos globales, de función, clase y bloque;
- reportar diagnósticos con categoría, mensaje, línea y columna;
- mostrar el árbol sintáctico, los errores y la tabla de símbolos desde el IDE;
- ejecutar casos exitosos y fallidos para cada regla evaluada.

## Criterios de entrega

| Componente | Peso |
|---|---:|
| IDE funcional para código `.cps` | 15 puntos |
| Analizador sintáctico y semántico, árbol y pruebas | 60 puntos |
| Tabla de símbolos con entornos anidados | 25 puntos |

Los puntos son criterios del producto final, no una forma de calificar individualmente a los integrantes.

## Arquitectura objetivo

```text
src/
├── compiscript/
│   ├── __init__.py
│   ├── grammar/
│   │   └── Compiscript.g4
│   ├── generated/
│   │   ├── __init__.py
│   │   ├── CompiscriptLexer.py
│   │   ├── CompiscriptParser.py
│   │   └── CompiscriptVisitor.py
│   ├── parser.py
│   └── analyzer.py
├── semantic/
│   ├── __init__.py
│   ├── diagnostics.py
│   ├── types.py
│   ├── expressions.py
│   ├── symbol_table.py
│   ├── functions.py
│   ├── control_flow.py
│   └── classes.py
├── gui/
│   ├── app.py
│   └── compiscript_tab.py
└── utils/
    └── visualizer.py

tests/
└── semantic/
    ├── fixtures/
    ├── test_parser.py
    ├── test_types.py
    ├── test_arrays.py
    ├── test_scopes.py
    ├── test_functions.py
    ├── test_control_flow.py
    ├── test_classes.py
    └── test_end_to_end.py
```

`grammar/` contiene la fuente editable y `generated/` contiene únicamente la salida de ANTLR. No se usarán dos ubicaciones distintas para los mismos archivos generados.

## Fase 0 — Contrato común

- [ ] Obtener la gramática oficial directamente del material del curso.
- [ ] Registrar la versión de ANTLR usada para generar el parser.
- [ ] Resolver las contradicciones de [REGLAS_Y_DECISIONES.md](REGLAS_Y_DECISIONES.md).
- [ ] Definir las interfaces mínimas `ParseResult`, `AnalysisResult`, `Diagnostic`, `Type`, `Symbol` y `SymbolTable`.
- [ ] Crear un programa `.cps` mínimo que el parser acepte.
- [ ] Acordar nombres de métodos y módulos antes de desarrollar en paralelo.

Esta fase debe integrarse primero. Después, los cuatro frentes pueden avanzar en paralelo.

## Fase 1 — Parser y fundamentos

- [ ] Generar Lexer, Parser y Visitor de ANTLR.
- [ ] Implementar recolección de errores léxicos y sintácticos sin detener la aplicación.
- [ ] Implementar tipos primitivos, arreglos, funciones, clases y el tipo centinela de error.
- [ ] Implementar la tabla de símbolos y el árbol de entornos.
- [ ] Agregar pruebas unitarias del parser, tipos y tabla de símbolos.

## Fase 2 — Reglas semánticas

- [ ] Declaraciones, inferencia y asignaciones.
- [ ] Operaciones aritméticas, lógicas y comparaciones.
- [ ] Listas, índices y asignación de elementos.
- [ ] Resolución de nombres, redeclaración y shadowing.
- [ ] Funciones, parámetros, retornos, recursión y closures.
- [ ] Condiciones, bucles, `break`, `continue`, `return` y código muerto.
- [ ] Clases, constructores, `this`, atributos y métodos.
- [ ] Al menos un caso exitoso y uno fallido por cada regla.

## Fase 3 — IDE y visualización

- [ ] Crear `CompiscriptTab` sin mezclar su lógica con la interfaz YAPar existente.
- [ ] Integrarla explícitamente en `MainWindow` de `src/gui/app.py`.
- [ ] Permitir abrir, editar y guardar `.cps`.
- [ ] Ejecutar el análisis fuera del hilo principal de Qt.
- [ ] Mostrar árbol sintáctico, diagnósticos y tabla de símbolos.
- [ ] Agregar al menos una prueba de integración sin interfaz y una prueba manual documentada de GUI.

## Fase 4 — Integración y entrega

- [ ] Ejecutar las regresiones de las fases anteriores.
- [ ] Ejecutar `pytest tests/semantic/` desde un entorno limpio.
- [ ] Verificar casos de recuperación después de múltiples errores.
- [ ] Confirmar que los archivos generados se puedan importar con la versión instalada del runtime.
- [ ] Actualizar el README con instrucciones reales de ejecución.
- [ ] Revisar que cada integrante tenga commits propios y trazables.

## Estrategia de pruebas

El objetivo no es alcanzar una cantidad arbitraria de tests. Se mantendrá una matriz que relacione cada requisito con:

- un caso exitoso;
- un caso fallido;
- la categoría esperada;
- la ubicación esperada cuando aplique;
- el responsable del código y de la prueba.

Quien implementa una regla también implementa sus pruebas. `test_end_to_end.py` valida la integración completa y no sustituye las pruebas por dominio.

## Flujo de Git

1. Crear cada rama desde `feature/fase3-compiscript` actualizado.
2. Hacer commits pequeños y de un solo autor.
3. Abrir PRs por capacidad completa: implementación, pruebas y documentación correspondiente.
4. Revisar los contratos compartidos antes de hacer merge.
5. Integrar continuamente; ningún integrante debe esperar a que termine todo otro frente.

## Definición de terminado

Una tarea se considera terminada cuando:

- el código implementa una regla confirmada;
- incluye casos exitosos y fallidos;
- no rompe las regresiones léxicas y sintácticas;
- está documentada sin afirmar capacidades inexistentes;
- fue revisada por al menos otro integrante.

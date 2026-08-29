# Plan de implementación — Fase 3

## Objetivo

Conservar las fases 1 y 2, cargar gramáticas ANTLR `.g4` en tiempo de ejecución
y construir análisis semántico configurable sin codificar una gramática
específica dentro del motor.

## Estrategia de ejecución

El plan usa exclusivamente una cadena secuencial de cuatro bloques:

```text
Base multimodo → Daniel → Nadissa → Dulce → Nelson → Entrega
```

Cada bloque comienza después de integrar y aceptar el anterior. Su responsable
termina implementación, pruebas y documentación de API antes de entregar. Un
integrante no vuelve a programar en bloques posteriores.

## Criterios del producto

- IDE multimodo.
- Gramática y regla inicial seleccionables en tiempo de ejecución.
- Creación, apertura, edición, guardado y compilación de `.cps`.
- Perfil semántico seleccionado como dato.
- Árbol con ubicaciones, alternativas y representación visual.
- Recorrido semántico mediante Listener o Visitor de ANTLR.
- Diagnósticos acumulados.
- Tabla de símbolos con scopes persistentes.
- Pruebas con Compiscript y otra gramática.
- Regresiones YALex/YAPar intactas.

## Base multimodo — precondición

- [x] Mantener YALex + YAPar.
- [x] Crear `src/antlr_mode/`.
- [x] Inspeccionar gramáticas `.g4`.
- [x] Descubrir reglas y elegir inicio.
- [x] Descargar o resolver ANTLR 4.13.2.
- [x] Generar Python en caché ignorada.
- [x] Cargar Lexer y Parser dinámicamente.
- [x] Recolectar errores léxicos y sintácticos.
- [x] Convertir al árbol común.
- [x] Integrar modo, archivo `.g4` y regla inicial en GUI.
- [x] Mostrar tokens, árbol y diagnósticos sintácticos.
- [x] Probar Compiscript y MiniCalc.
- [x] Ejecutar regresiones de fases anteriores.

Antes de iniciar el bloque 1 se congelan las APIs de `GrammarInfo`,
`AntlrAnalysisResult` y `ParseTreeNode`.

## Bloque 1 — Daniel: núcleo semántico

- [ ] Implementar `SourceLocation`, `Diagnostic` y `DiagnosticBag`.
- [ ] Implementar la jerarquía `Type`.
- [ ] Definir compatibilidad, promoción y tipo común.
- [ ] Implementar `SemanticValue`.
- [ ] Implementar acciones de literales y expresiones.
- [ ] Probar diagnósticos, tipos, operadores, asignaciones, arreglos e índices.
- [ ] Cubrir `TYP-*`, `LST-*` y `GEN-02` asignados en la matriz.
- [ ] Documentar y congelar las APIs públicas.

Puerta de salida: las pruebas usan valores directos, no ANTLR, árboles, perfiles
o GUI. Nadissa puede construir el motor sin solicitar cambios a Daniel.

## Bloque 2 — Nadissa: motor semántico

- [ ] Implementar `Symbol`, `Scope` y `SymbolTable`.
- [ ] Conservar scopes cerrados para el IDE.
- [ ] Definir y validar el esquema de perfiles JSON.
- [ ] Implementar `ActionRegistry` seguro.
- [ ] Implementar `SemanticContext` y `SemanticEvaluator`.
- [ ] Implementar acciones de declaraciones, funciones, control y clases.
- [ ] Implementar recursión, funciones anidadas y closures.
- [ ] Implementar control contextual de `break`, `continue` y `return`.
- [ ] Implementar acceso a miembros, constructor y `this`.
- [ ] Detectar código muerto y duplicación de variables o parámetros.
- [ ] Definir `SemanticAnalysisResult`.
- [ ] Probar el motor con árboles construidos manualmente.
- [ ] Cubrir `SCP-*`, `FUN-*`, `CTL-*`, `CLS-*`, `GEN-01` y `GEN-03`.
- [ ] Documentar nombres de acciones y selectores disponibles.

Puerta de salida: dos árboles con nombres distintos pueden usar perfiles
distintos y las mismas acciones sin cambiar Python. Dulce puede conectar ANTLR
sin solicitar cambios a Nadissa.

## Bloque 3 — Dulce: conexión ANTLR-semántica

- [ ] Completar casos de error y regresión del frontend ANTLR.
- [ ] Confirmar metadatos suficientes en `ParseTreeNode`.
- [ ] Exponer de forma controlada el árbol nativo de la sesión ANTLR.
- [ ] Implementar `SemanticTreeListener` y recorrerlo con
  `ParseTreeWalker.DEFAULT.walk` o usar un Visitor equivalente.
- [ ] Implementar `analyze_semantics_with_g4`.
- [ ] Evitar semántica cuando la sintaxis no fue aceptada.
- [ ] Validar perfiles contra la colección de reglas de `GrammarInfo`.
- [ ] Crear un perfil semántico pequeño para MiniCalc.
- [ ] Probar dos gramáticas consecutivamente sin cambiar el motor.
- [ ] Cubrir `ANT-01` a `ANT-06`.
- [ ] Validar la gramática oficial o confirmar antes del cierre que usa una
  forma ANTLR ya soportada.
- [ ] Documentar la API que consumirá el IDE.

Puerta de salida: desde Python se obtienen sintaxis, diagnósticos semánticos y
símbolos para una gramática y perfil elegidos en tiempo de ejecución. Nelson no
necesita modificar el adaptador.

## Bloque 4 — Nelson: IDE y entrega

- [ ] Crear el perfil semántico de Compiscript.
- [ ] Crear, abrir, editar y guardar archivos `.cps` desde el IDE.
- [ ] Compilar el contenido completo del `.cps` actual.
- [ ] Permitir elegir o resolver el perfil desde el IDE.
- [ ] Ejecutar sintaxis y semántica fuera del hilo principal.
- [ ] Mostrar diagnósticos sintácticos y semánticos.
- [ ] Mostrar scopes y símbolos.
- [ ] Mostrar el árbol como nodos y aristas mediante Graphviz o vista
  jerárquica equivalente.
- [ ] Distinguir warnings y errores.
- [ ] Conservar resultados ANTLR y YAPar.
- [ ] Crear pruebas end-to-end.
- [ ] Actualizar README y procedimiento de prueba manual.
- [ ] Ejecutar la matriz completa de regresión.
- [ ] Cubrir `IDE-01` a `IDE-08`.

Puerta de salida: una sola ventana ejecuta ambos modos y no existen tareas de
implementación pendientes para Daniel, Nadissa o Dulce.

## Verificación de entrega

- [ ] Ejecutar `python -m pytest tests/antlr_mode -q`.
- [ ] Ejecutar `python -m pytest tests/semantic -q`.
- [ ] Probar 75 entradas válidas anteriores.
- [ ] Probar 8 entradas negativas anteriores.
- [ ] Probar Compiscript y MiniCalc sin cambios Python.
- [ ] Confirmar que cada ID de `MATRIZ_CUMPLIMIENTO.md` tiene evidencia.
- [ ] Ejecutar una demostración desde `.cps` hasta árbol, errores y símbolos.
- [ ] Verificar Java, Graphviz y modo sin red con caché.
- [ ] Confirmar que `output/` está limpio en Git.
- [ ] Revisar commits individuales.
- [ ] Confirmar que la documentación coincide con el código entregado.
- [ ] Confirmar que se usa la gramática oficial más reciente y actualizar el
  perfil si cambió.

## Flujo de Git secuencial

1. Daniel crea `feature/fase3-01-semantic-core` desde la rama base.
2. Se prueba, revisa e integra completamente su bloque.
3. Nadissa crea `feature/fase3-02-semantic-engine` desde esa integración.
4. Se prueba, revisa e integra completamente su bloque.
5. Dulce crea `feature/fase3-03-antlr-semantic` desde esa integración.
6. Se prueba, revisa e integra completamente su bloque.
7. Nelson crea `feature/fase3-04-ide-delivery` desde esa integración.
8. Se prueba e integra la entrega final.

Las revisiones no autorizan a repartir correcciones pendientes entre bloques.
El propietario corrige su bloque antes de que comience el siguiente.

## Definición de bloque terminado

Un bloque termina cuando:

- implementa todas sus responsabilidades;
- incluye casos exitosos y fallidos;
- pasa sus pruebas y las regresiones disponibles;
- documenta las APIs consumidas por el siguiente bloque;
- no contiene tareas pendientes para completar después;
- queda integrado antes de crear la rama siguiente.

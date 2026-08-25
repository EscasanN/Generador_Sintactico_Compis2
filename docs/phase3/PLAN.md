# Plan de implementación — Fase 3

## Objetivo

Conservar las fases 1 y 2, agregar carga dinámica de gramáticas ANTLR `.g4` y
construir análisis semántico sin codificar una gramática específica dentro del
motor.

## Criterios del producto

- IDE multimodo.
- Gramática seleccionable en tiempo de ejecución.
- Árbol con ubicaciones y alternativas.
- Diagnósticos acumulados.
- Tabla de símbolos con scopes.
- Pruebas con Compiscript y otra gramática.
- Regresiones YALex/YAPar intactas.

## Fase 0 — Base multimodo

- [x] Mantener YALex + YAPar.
- [x] Crear `src/antlr_mode/`.
- [x] Inspeccionar gramáticas `.g4`.
- [x] Descubrir reglas y elegir inicio.
- [x] Descargar o resolver ANTLR 4.13.2.
- [x] Generar Python en caché ignorada.
- [x] Cargar Lexer y Parser dinámicamente.
- [x] Recolectar errores léxicos y sintácticos.
- [x] Convertir al árbol común.
- [x] Integrar modo, archivo G4 y regla inicial en GUI.
- [x] Mostrar tokens, árbol y diagnósticos.
- [x] Probar Compiscript y MiniCalc.
- [x] Ejecutar regresiones de fases anteriores.

## Fase 1 — Contratos semánticos

- [ ] Confirmar cómo se entregarán las reglas semánticas.
- [ ] Definir `Diagnostic` y `DiagnosticBag`.
- [ ] Definir jerarquía `Type`.
- [ ] Definir `SemanticValue`.
- [ ] Definir `Symbol`, `Scope` y `SymbolTable`.
- [ ] Definir esquema JSON del perfil.
- [ ] Definir `SemanticAnalysisResult`.
- [ ] Congelar firmas antes del trabajo paralelo.

## Fase 2 — Motor genérico

- [ ] Cargar y validar perfiles.
- [ ] Resolver bindings por alternativa y regla.
- [ ] Crear registro seguro de acciones.
- [ ] Recorrer `ParseTreeNode`.
- [ ] Implementar scopes persistentes.
- [ ] Implementar tipos y valores.
- [ ] Acumular diagnósticos.
- [ ] Rechazar reglas, selectores y acciones desconocidas.
- [ ] Probar el motor con árboles manuales y ANTLR.

## Fase 3 — Reglas semánticas

- [ ] Declaraciones y resolución.
- [ ] Inferencia y asignación.
- [ ] Operadores y comparación.
- [ ] Listas e índices.
- [ ] Funciones, llamadas y retornos.
- [ ] Control de flujo y código muerto.
- [ ] Clases, miembros, constructores y `this`.
- [ ] Caso exitoso y fallido por regla confirmada.

Estas capacidades son acciones genéricas. El perfil decide qué regla gramatical
las invoca.

## Fase 4 — IDE semántico

- [ ] Seleccionar perfil semántico o detectarlo de forma acordada.
- [ ] Ejecutar semántica fuera del hilo principal.
- [ ] Mostrar diagnósticos sintácticos y semánticos.
- [ ] Mostrar árbol de scopes y símbolos.
- [ ] Distinguir warnings y errores.
- [ ] Conservar resultados ANTLR y YAPar.
- [ ] Documentar prueba manual.

## Fase 5 — Entrega

- [ ] Ejecutar `python -m pytest tests/antlr_mode -q`.
- [ ] Ejecutar `python -m pytest tests/semantic -q`.
- [ ] Probar 75 entradas válidas anteriores.
- [ ] Probar 8 entradas negativas anteriores.
- [ ] Probar Compiscript y MiniCalc sin cambios Python.
- [ ] Verificar Java, Graphviz y modo sin red con caché.
- [ ] Confirmar que `output/` está limpio en Git.
- [ ] Revisar commits individuales.
- [ ] Actualizar instrucciones finales.

## Flujo de Git

1. Actualizar desde `feature/fase3-compiscript`.
2. Crear la rama asignada.
3. Mantener un propietario por archivo.
4. Hacer commits pequeños.
5. Incluir pruebas y documentación del contrato.
6. Abrir PR y recibir revisión externa.
7. Integrar continuamente.

## Definición de terminado

Una tarea termina cuando funciona con contratos propios, incluye éxito y error,
no acopla el motor a Compiscript, no rompe regresiones y está revisada.

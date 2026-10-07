# División del trabajo — Proyecto 2

## Regla de dependencia

La división mantiene el modelo de la fase anterior: bloques secuenciales,
propiedad clara de archivos y una puerta de aceptación antes de comenzar el
siguiente bloque.

~~~text
Base: Compiscript sintáctico y semántico
        │
        v
Daniel — IR, temporales y expresiones
        │
        v
Nadissa — anotaciones, símbolos y frames
        │
        v
Dulce — control, funciones, objetos y pipeline
        │
        v
Nelson — IDE, CLI, fixtures y documentación final
~~~

Se permiten dependencias hacia adelante: un bloque usa contratos ya integrados.
No se permiten dependencias hacia atrás: si un contrato no basta, se detecta y
corrige antes de cerrar la puerta del bloque propietario.

## Resumen del equipo

| Orden | Integrante | Bloque | Rama |
|---:|---|---|---|
| 1 | Daniel Chet | IR, temporales, verificador y lowering de expresiones | feature/proyecto2-01-ir-core |
| 2 | Nadissa Vela | Anotaciones semánticas, tabla extendida y activaciones | feature/proyecto2-02-runtime-layout |
| 3 | Dulce Ambrosio | Lowering de sentencias, funciones, objetos y pipeline | feature/proyecto2-03-tac-generator |
| 4 | Nelson Escalante | IDE, CLI, fixtures, regresión y entrega | feature/proyecto2-04-ide-delivery |

La distribución equilibra dependencias, no puntos de la rúbrica. La generación
de TAC de 65 puntos está compartida entre los bloques 1, 3 y 4; la tabla
extendida pertenece al bloque 2.

## Bloque 1 — Daniel Chet

### Propiedad principal

~~~text
src/codegen/__init__.py
src/codegen/contracts.py
src/codegen/ir.py
src/codegen/builder.py
src/codegen/names.py
src/codegen/verifier.py
src/codegen/formatter.py
src/codegen/expression_lowering.py
tests/codegen/test_ir.py
tests/codegen/test_builder.py
tests/codegen/test_temporaries.py
tests/codegen/test_verifier.py
tests/codegen/test_expression_lowering.py
docs/proyecto2/DISENO_TAC.md
~~~

### Entrega

- cuádruplos tipados;
- programa y procedimientos;
- emisión y formato determinista;
- pool de temporales con adquisición y liberación;
- generador de etiquetas;
- verificador de definición, usos y saltos;
- expresiones aritméticas, lógicas, relacionales y asignaciones;
- cortocircuito, ternario e interfaces para lista/campo/llamada;
- protocolos que los bloques posteriores implementan.

### Límite

Daniel no modifica la tabla de símbolos, la GUI ni el adaptador ANTLR. Sus
pruebas usan árboles pequeños y una implementación falsa de SemanticFacts.

## Bloque 2 — Nadissa Vela

### Propiedad principal

~~~text
src/semantic/results.py
src/semantic/evaluator.py
src/semantic/antlr_listener.py
src/codegen/semantic_facts.py
src/codegen/layout.py
src/codegen/activation.py
tests/semantic/test_codegen_annotations.py
tests/codegen/test_semantic_facts.py
tests/codegen/test_layout.py
tests/codegen/test_activation.py
~~~

Si una prueba demuestra que se necesita una asociación adicional al abrir un
scope, Nadissa puede tocar la acción semántica estrictamente necesaria y debe
preservar sus firmas y regresiones.

### Entrega

- valores, símbolos y scopes consultables por nodo;
- extensión compatible de SemanticAnalysisResult;
- tamaño, alineación, dirección y offset por símbolo;
- etiquetas únicas para callables;
- layout de campos de clase;
- descriptor de registro de activación;
- control link, access link y distancia léxica;
- identificación de capturas;
- reserva de slots temporales.

### Límite

Nadissa no emite sentencias TAC ni presenta resultados en Qt. Entrega datos y
APIs consumibles por el generador de Dulce.

## Bloque 3 — Dulce Ambrosio

### Propiedad principal

~~~text
src/codegen/statements.py
src/codegen/control_flow.py
src/codegen/callables.py
src/codegen/objects.py
src/codegen/generator.py
src/codegen/results.py
src/codegen/pipeline.py
tests/codegen/test_statements.py
tests/codegen/test_control_flow.py
tests/codegen/test_callables.py
tests/codegen/test_closures.py
tests/codegen/test_objects.py
tests/codegen/test_lists.py
tests/codegen/test_pipeline.py
~~~

### Entrega

- traducción de todas las sentencias mínimas;
- pilas correctas para break y continue;
- procedimientos, llamadas, parámetros y retornos;
- recursión y closures;
- creación de objetos, campos, métodos y this;
- listas e índices;
- pipeline que ejecuta codegen solo después de semántica aceptada;
- resultado inmutable con TAC, layout y diagnósticos;
- cobertura explícita de cada alternativa soportada.

### Límite

Dulce consume IRBuilder, ExpressionLowerer y layouts públicos. No cambia sus
helpers internos. Tampoco agrega lógica de generación dentro del perfil
semántico o la GUI.

## Bloque 4 — Nelson Escalante

### Propiedad principal

~~~text
src/main.py
src/gui/app.py
src/gui/codegen_results.py
src/gui/semantic_results.py
tests/test_main_cli.py
tests/gui/test_cps_workflow.py
tests/gui/test_codegen_results.py
tests/cps/codegen/
README.md
docs/proyecto2/
~~~

Nelson puede actualizar los documentos de planificación únicamente para
reflejar el comportamiento real integrado, sin borrar la autoría ni las
decisiones de los bloques previos.

### Entrega

- acción Compilar en el IDE;
- pestaña de TAC;
- tabla extendida y frames navegables;
- diagnósticos de todas las fases;
- CLI para imprimir o exportar TAC;
- batería .cps completa con resultados esperados;
- guía de ejecución y demostración;
- suite de regresión y auditoría de entrega.

### Límite

La interfaz no calcula offsets, tipos, etiquetas o saltos. Solo transforma
CompilationResult en vistas y archivos.

## Puertas de aceptación

| Puerta | Condición para continuar |
|---|---|
| Base → Daniel | Suite actual verde, gramática/perfil compatibles y diseño TAC acordado. |
| Daniel → Nadissa | IR y expresiones pasan pruebas con SemanticFacts falso; APIs documentadas. |
| Nadissa → Dulce | Árbol real expone hechos y layouts; frames y capturas pasan pruebas. |
| Dulce → Nelson | compile_compiscript produce TAC verificado o diagnósticos sin TAC. |
| Nelson → entrega | IDE y CLI demuestran el flujo completo; matriz y suite están verdes. |

## Reglas de colaboración

- Una persona propietaria por archivo durante su bloque.
- La rama siguiente se crea desde la integración aceptada de la anterior.
- Cada requisito incluye prueba exitosa y fallida cuando aplica.
- Cada Pull Request muestra qué IDs de la matriz cierra.
- Los commits deben ser individuales; no se comparte una cuenta.
- Los revisores comentan, pero el propietario corrige antes de integrar.
- Una API aceptada no cambia silenciosamente en un bloque posterior.
- Los módulos nuevos no importan PyQt6 fuera de src/gui.
- La generación no ejecuta eval, exec ni código configurado desde JSON.
- No se versionan output/antlr, imágenes generadas, cachés ni TAC temporales.
- Una entrada semánticamente inválida nunca produce un TAC parcial presentado
  como válido.

## Evidencia mínima por integrante

Cada integrante debe dejar:

1. al menos un commit de implementación;
2. al menos un commit de pruebas o un commit único que incluya pruebas claras;
3. descripción del contrato público entregado;
4. comandos ejecutados y resultado;
5. caso positivo y caso negativo propio;
6. Pull Request o registro equivalente de revisión.

## Checklist de cada Pull Request

- [ ] Modifica solamente los archivos de su bloque o documenta la excepción.
- [ ] Indica IDs de MATRIZ_CUMPLIMIENTO.md.
- [ ] Incluye pruebas unitarias y de integración proporcionales.
- [ ] Mantiene las pruebas de bloques anteriores.
- [ ] No cambia Compiscript.g4 sin decisión registrada.
- [ ] No rompe el fingerprint del perfil.
- [ ] No deja TODO necesario para el bloque siguiente.
- [ ] Documenta APIs nuevas y errores esperados.
- [ ] Ejecuta formateo, pruebas propias y regresiones.
- [ ] Cumple la puerta antes de integrar.

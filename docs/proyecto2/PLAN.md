# Plan de implementación — Proyecto 2

## Objetivo

Extender el compilador actual para que, después de aceptar sintáctica y
semánticamente un archivo .cps, produzca código de tres direcciones, recicle
temporales y muestre una tabla de símbolos complementada con offsets, tamaños,
etiquetas y registros de activación.

El plan conserva la entrega semántica calificada y agrega una fase nueva con
contratos propios.

## Estrategia de ejecución

Se usan cuatro bloques secuenciales y cerrados:

~~~text
Base Compiscript aceptada
        ↓
1. Daniel — IR, temporales y expresiones
        ↓
2. Nadissa — anotaciones, layouts y activaciones
        ↓
3. Dulce — lowering completo y pipeline
        ↓
4. Nelson — IDE, CLI, fixtures y entrega
        ↓
Auditoría final del equipo
~~~

Cada rama nace después de integrar y aceptar la anterior. El responsable de un
bloque termina implementación, pruebas y documentación de sus APIs antes del
siguiente handoff. Una persona no deja trabajo para volver a completar su
bloque al final.

## Criterios del producto final

- Entrada desde archivo Compiscript .cps.
- Lexer, parser y análisis semántico vigentes sin regresiones.
- Generación de TAC únicamente después de un análisis aceptado.
- IR estructurada mediante cuádruplos y serialización textual estable.
- Operaciones aritméticas, lógicas, comparaciones y asignaciones.
- if/else, while, do-while, for y switch mediante etiquetas y saltos.
- break y continue con destinos correctos en bucles anidados.
- Funciones, parámetros, llamadas, retornos y recursión.
- Funciones anidadas y closures con entorno de definición.
- Creación de objetos, constructor, atributos, métodos y this.
- Creación y acceso indexado de listas.
- Asignación y reciclaje verificable de temporales.
- Símbolos con almacenamiento, tamaño, offset, etiqueta y nivel léxico.
- Registros de activación con retorno, enlaces, parámetros, locales y
  temporales.
- TAC, diagnósticos y tabla extendida visibles desde IDE y CLI.
- Pruebas positivas, negativas y de invariantes internos.

## Base — precondición

- [ ] Crear una rama de integración desde refactor/compiscript-only.
- [ ] Ejecutar la suite completa y registrar el resultado base.
- [ ] Confirmar que Compiscript.g4 y su perfil tienen fingerprint compatible.
- [ ] Congelar las APIs públicas de análisis sintáctico y semántico.
- [ ] Confirmar que tests/cps/demostracion-valida.cps produce ACCEPT.
- [ ] Confirmar que un programa inválido no llega a una fase posterior.
- [ ] Acordar el diseño de [DISENO_TAC.md](DISENO_TAC.md).
- [ ] Resolver o registrar las preguntas críticas de
  [REGLAS_Y_DECISIONES.md](REGLAS_Y_DECISIONES.md).

Puerta de entrada: la suite actual pasa y no hay cambios pendientes de la fase
semántica mezclados con el nuevo proyecto.

## Bloque 1 — Daniel: IR, temporales y expresiones

- [ ] Crear el paquete src/codegen sin acoplarlo a Qt.
- [ ] Definir operandos, opcodes, instrucciones, procedimientos y programa IR.
- [ ] Implementar IRBuilder y el formato textual determinista.
- [ ] Implementar generadores de etiquetas y TemporaryPool.
- [ ] Implementar el verificador de forma básica.
- [ ] Definir el protocolo de hechos semánticos que consumirá el lowering.
- [ ] Traducir literales, identificadores, operaciones unarias y binarias.
- [ ] Traducir comparaciones, asignaciones y expresión ternaria.
- [ ] Implementar cortocircuito real para && y ||.
- [ ] Proveer primitivas de lista, índice, campo, llamada y closure para los
  bloques posteriores.
- [ ] Probar reciclaje seguro y máximo de temporales vivos.
- [ ] Convertir DISENO_TAC.md en contrato vigente de su implementación.
- [ ] Cubrir IR-*, EXP-* y TMP-* asignados en la matriz.

Puerta Daniel → Nadissa: la IR puede construirse, formatearse y verificarse con
hechos semánticos simulados; las expresiones producen TAC sin depender de la
GUI ni modificar la fase semántica.

## Bloque 2 — Nadissa: tabla extendida y entorno de ejecución

- [ ] Exponer anotaciones semánticas inmutables por nodo sin romper la API
  existente.
- [ ] Registrar el scope activo después de las acciones de entrada.
- [ ] Asociar expresiones y declaraciones con su Symbol resuelto.
- [ ] Implementar el adaptador SemanticFacts definido por Daniel.
- [ ] Definir tamaños y alineaciones del modelo abstracto.
- [ ] Calcular direcciones globales y offsets de parámetros, locales y campos.
- [ ] Asignar etiquetas estables a funciones, métodos y clases.
- [ ] Implementar SymbolLayoutTable como extensión de la tabla existente.
- [ ] Implementar ActivationRecordLayout y su builder.
- [ ] Diferenciar enlace de control y enlace de acceso.
- [ ] Detectar capturas y calcular distancia léxica.
- [ ] Reservar slots según el máximo de temporales vivos.
- [ ] Probar layouts, alineación, scopes anidados y closures.
- [ ] Cubrir SYM-* y RUN-* asignados en la matriz.

Puerta Nadissa → Dulce: dado un árbol ya analizado, cualquier nodo relevante
puede consultar tipo, símbolo, scope y ubicación; cada declaración tiene layout
y cada función dispone de un descriptor de activación construible.

## Bloque 3 — Dulce: lowering completo y pipeline

- [ ] Implementar el generador Compiscript sobre ParseTreeNode.
- [ ] Traducir declaraciones, copias y asignaciones de elementos o miembros.
- [ ] Traducir if/else, while, do-while, for y switch.
- [ ] Mantener pilas separadas de break y continue con destinos correctos.
- [ ] Traducir funciones, parámetros, llamadas y retornos.
- [ ] Demostrar recursión directa y mutua con etiquetas predeclaradas.
- [ ] Traducir funciones anidadas y creación/acceso de closures.
- [ ] Traducir clases, objetos, constructor, campos, métodos y this.
- [ ] Traducir listas, cargas y almacenamientos indexados.
- [ ] Cubrir print, módulo, ternario, foreach y herencia de la gramática actual.
- [ ] Definir una salida explícita para try/catch o un diagnóstico de
  construcción no soportada acordado con el profesor.
- [ ] Crear IntermediateCodeResult y CompilationResult.
- [ ] Implementar compile_compiscript sin cambiar
  analyze_semantics_with_g4.
- [ ] Impedir TAC cuando sintaxis o semántica reporten errores.
- [ ] Ejecutar el verificador antes de aceptar la compilación.
- [ ] Cubrir CTL-*, FUN-*, CLS-*, LST-* y PIPE-*.

Puerta Dulce → Nelson: desde Python, un .cps válido produce TAC verificado,
tabla extendida y frames; uno inválido conserva sus diagnósticos y no produce
TAC.

## Bloque 4 — Nelson: IDE, CLI y entrega

- [ ] Cambiar la acción principal del IDE de Analizar a Compilar.
- [ ] Mantener la ejecución fuera del hilo principal de Qt.
- [ ] Agregar vista de TAC con copia y exportación opcional.
- [ ] Mostrar diagnósticos de frontend, semántica y generación.
- [ ] Mostrar tabla extendida y registros de activación.
- [ ] Mantener árbol sintáctico y tabla semántica existentes.
- [ ] Agregar opción CLI para imprimir o guardar TAC.
- [ ] Crear fixtures .cps por cada ID obligatorio.
- [ ] Crear salidas esperadas estables para casos representativos.
- [ ] Probar que entradas inválidas nunca muestran TAC antiguo.
- [ ] Actualizar README principal e instrucciones de ejecución.
- [ ] Preparar una demostración válida y una fallida.
- [ ] Ejecutar regresión completa y revisar los commits individuales.
- [ ] Cubrir IDE-*, OUT-* y TST-*.

Puerta Nelson → entrega: una sola ventana permite editar y compilar .cps,
presenta TAC y tabla extendida, y la suite completa pasa desde un clon limpio.

## Orden de prioridades

### Prioridad 1 — evita perder la calificación

1. Modelo TAC y documentación consistente.
2. Expresiones, control mínimo, funciones, clases y listas exigidas.
3. Reciclaje comprobable de temporales.
4. Tabla extendida y registros de activación.
5. Flujo completo desde IDE.
6. Pruebas positivas y negativas.

### Prioridad 2 — evita fallos con programas ya aceptados

1. Cortocircuito y orden de evaluación.
2. Recursión y funciones anidadas.
3. Asignación a lista y campo.
4. Constructor implícito y this.
5. Foreach, ternario, módulo, print e herencia.
6. Diagnóstico explícito para toda alternativa de la gramática.

### Prioridad 3 — mejoras posteriores

- exportar TAC a archivo;
- colores o navegación desde TAC hacia la fuente;
- métricas del número máximo de temporales;
- visualización de frames.

Estas mejoras no pueden retrasar los requisitos de las prioridades anteriores.

## Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Generar desde texto en vez del árbol | pierde precedencia y resolución | consumir ParseTreeNode y anotaciones |
| Repetir validación semántica en codegen | reglas contradictorias | usar hechos semánticos como contrato |
| Modificar la gramática para facilitar TAC | rompe perfil y pruebas | no cambiarla salvo defecto confirmado |
| No conservar resultados por nodo | no se sabe qué Symbol usa un id | exponer SemanticAnnotations en bloque 2 |
| Reciclar un temporal demasiado pronto | TAC incorrecto | ownership explícito y verificador |
| Evaluar ambas ramas de &&, || o ternario | cambia efectos laterales | lowering por etiquetas |
| Confundir static link con caller | closures incorrectas | enlaces separados y pruebas de anidamiento |
| Función no void cae al final | retorno indefinido | confirmar política y no inventar valores |
| Tratar texto TAC como estructura | pruebas frágiles | IR tipada como fuente de verdad |
| Añadir GDA sin alias/versiones | elimina cálculos necesarios | dejar optimización fuera del alcance |
| Aceptar nodos sin lowering | programa ACCEPT sin código completo | cobertura de alternativas y error IR |
| Hacer codegen en el hilo de Qt | IDE bloqueado | reutilizar worker |

## Flujo de Git secuencial

1. Crear **feature/proyecto2-codegen** desde refactor/compiscript-only.
2. Daniel crea **feature/proyecto2-01-ir-core** desde la integración.
3. Revisar, corregir e integrar completamente el bloque 1.
4. Nadissa crea **feature/proyecto2-02-runtime-layout** desde la nueva
   integración.
5. Revisar, corregir e integrar completamente el bloque 2.
6. Dulce crea **feature/proyecto2-03-tac-generator** desde la nueva
   integración.
7. Revisar, corregir e integrar completamente el bloque 3.
8. Nelson crea **feature/proyecto2-04-ide-delivery** desde la nueva
   integración.
9. Revisar, corregir e integrar completamente el bloque 4.
10. Crear una rama final de correcciones solo si la auditoría encuentra un
    incumplimiento transversal y conservar esos commits separados.

## Verificación final prevista

~~~powershell
python -m pytest tests/codegen -q
python -m pytest tests/semantic -q
python -m pytest tests/antlr_mode -q
python -m pytest tests/gui -q
python -m pytest tests -q
python -m src.main --cps tests/cps/codegen/validos/DEMO-completa.cps --emit-tac
~~~

También se debe ejecutar manualmente el IDE con:

1. un programa válido completo;
2. un programa con error semántico;
3. un programa que demuestre temporales reciclados;
4. una función recursiva;
5. una closure;
6. una clase con constructor y lista.

## Definición global de terminado

- [ ] Todos los IDs de MATRIZ_CUMPLIMIENTO.md tienen evidencia.
- [ ] El lenguaje TAC coincide con DISENO_TAC.md.
- [ ] No existe TAC si una fase anterior falla.
- [ ] Cada alternativa soportada de Compiscript genera código o diagnóstico.
- [ ] El verificador acepta toda salida publicada.
- [ ] Los offsets y frames son visibles.
- [ ] IDE y CLI usan el mismo pipeline público.
- [ ] La suite completa pasa.
- [ ] README permite ejecutar desde un clon limpio.
- [ ] Cada integrante tiene commits propios y localizables.
- [ ] No quedan TODO obligatorios ni archivos generados en Git.

# Matriz global de cumplimiento de la fase 3

## Regla de aceptación

Estado: **los cuatro bloques aprobados y condiciones globales cumplidas**
(ver [la auditoría](AUDITORIA_FINAL.md)). Las cuatro matrices enlazan evidencia implementada y
ejecutada con MARS. Ver [la entrega de Daniel](entrega-bloque1-daniel.md),
[la de Nadissa](entrega-bloque2-nadissa.md), [la de Dulce](entrega-bloque3-dulce.md)
y [la de Nelson](entrega-bloque4-nelson.md).

Una fila cambia a APROBADO solo cuando existen sus pruebas versionadas,
se ejecutan con éxito sobre el commit declarado y se registra la evidencia.
La prueba negativa puede ser un rechazo de IR o un invariante si el frontend
impide construir un `.cps` que llegue a ese caso. No se exige inventar un
programa inválido que el parser acepte para probar un contrato interno.

Para cada ID, su entrega debe registrar: requisito, responsable, prueba positiva,
negativa/invariante, fixture cuando aplique, esperado, comando, resultado real,
commit y estado. Las matrices individuales contienen los escenarios y pruebas
previstas; [la plantilla](PLANTILLA_ENTREGA_BLOQUE.md) define el registro de ejecución.

## Trazabilidad de la rúbrica

| Componente oficial | Puntos | IDs de evidencia principal | Responsables |
|---|---:|---|---|
| Llamadas y retornos | 20 | ABI-01; CALL-01 a CALL-04; ENV-01 a ENV-03; METHOD-01 | Nadissa; Daniel provee registros y Dulce integra ejecución compuesta. |
| Asignación de registros o pila | 20 | MEM-01; REG-01 a REG-04 (`$t` y `$s`); FLOW-01; CALL-03 | Daniel; Nadissa valida su interacción con llamadas. |
| Código MIPS funcional y pruebas | 60 | CORE-01; NUM-01; SIM-01; STR-01; LIST-01; OBJ-01 a OBJ-03; EXC-01 a EXC-03; PIPE-01 y PIPE-02; E2E-01 | Los cuatro bloques. |
| Condiciones de entrega | Requisito para calificar | IDE-01 a IDE-04; CLI-01 y CLI-02; DOC-01; GIT-01; ACC-01 a ACC-08 | Nelson y equipo. |

Las extensiones completas son un acuerdo del equipo para conservar el lenguaje
actual. No se les asignan puntos oficiales adicionales ni se convierte esta
tabla en una garantía de nota.

## Matrices por integrante

| Bloque | Matriz canónica | Puerta |
|---|---|---|
| Daniel | [MATRIZ_BLOQUE1_DANIEL.md](MATRIZ_BLOQUE1_DANIEL.md) | IR escalar y derrames ejecutados en MARS. |
| Nadissa | [MATRIZ_BLOQUE2_NADISSA.md](MATRIZ_BLOQUE2_NADISSA.md) | Llamadas, recursión, entornos y closures ejecutados. |
| Dulce | [MATRIZ_BLOQUE3_DULCE.md](MATRIZ_BLOQUE3_DULCE.md) | Todos los dominios y opcodes por API `.cps`. |
| Nelson | [MATRIZ_BLOQUE4_NELSON.md](MATRIZ_BLOQUE4_NELSON.md) | IDE/CLI, instalación limpia y defensa reproducibles. |

## Condiciones globales

| ID | Requisito | Evidencia positiva y fallo que debe impedir aceptación | Responsable | Estado |
|---|---|---|---|---|
| ACC-01 | Base y regresión | Suite previa limpia y misma gramática/perfil; cualquier fallo no explicado bloquea cierre. | Daniel / equipo | APROBADO: 1267 pruebas sobre `9d495ad`, 0 fallos |
| ACC-02 | Cobertura del IR | Test `test_opcode_catalog_is_complete` compara handlers y enum; un opcode omitido no se ignora. | Dulce | APROBADO |
| ACC-03 | Ejecución real | Aceptación con MARS requerido, todos los `.cps` MIPS ejecutados; skip por herramienta ausente bloquea cierre. | Nelson | APROBADO: `test_e2e_01_*` ejecuta los 24 fixtures por CLI e IDE con `--require-mars` |
| ACC-04 | Evidencia por bloque | Cada ID enlaza prueba, esperado, comando y commit; archivo inexistente o prueba fallida revoca APROBADO. | Cada integrante | APROBADO: las cuatro entregas registran prueba, esperado, comando, commit y revisor por ID |
| ACC-05 | Compilación compatible | Pruebas previas y opciones TAC conservadas; rechazo previo nunca produce MIPS. | Dulce / Nelson | APROBADO: `tests/test_main_cli.py` sin cambios y `test_cli_02_exit_and_channels_rejection_keeps_existing_files` |
| ACC-06 | Entrega reproducible | Checkout limpio, JAR identificado por hash, README y demo reproducidos por otro integrante. | Nelson | APROBADO: checkout limpio repetido por Daniel (1263 pruebas) y demo visible ensayada el 2026-11-08 |
| ACC-07 | Autoría y modalidad | Commits propios de cuatro integrantes y autorización registrada; no inventar aprobación externa. | Equipo | APROBADO: commits propios de los cuatro integrantes, sin coautorías |
| ACC-08 | Demostración final | Ensayo IDE y CLI con válido, inválido, runtime, recursión y spills; incidencias bloqueantes resueltas. | Equipo | APROBADO: los 8 pasos del ensayo visible (válido, inválido, runtime, recursión, spills, cancelación y CLI) sin incidencias bloqueantes |

`ACC-*` registra condiciones globales y referencia las pruebas de los bloques;
no exige duplicar las mismas pruebas con otro nombre.

## Diferencia entre generar, ensamblar y ejecutar

`MipsCompilationResult.accepted` significa frontend y backend aceptados; aún
puede existir un error del programa al ejecutarlo. La ejecución aprobada exige
ensamblado válido, terminación prevista y resultado esperado. Un caso negativo
runtime aprueba su prueba si falla **como se esperaba**, no porque el simulador
haya sufrido cualquier error. Timeout, pasos agotados o herramienta ausente
son estados separados y no sustituyen una excepción del lenguaje.

La aceptación de una compilación exige cero errores de fases previas, IR
verificada, layouts resolubles, todos los opcodes traducidos y ensamblador
completo. Los warnings semánticos no se convierten en errores de esta fase.

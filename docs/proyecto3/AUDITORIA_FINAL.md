# Auditoría de integración y entrega MIPS

**Estado de integración global: LISTO PARA ENTREGA, salvo dos acciones del equipo**
(dictamen del bloque 2 y demo en ventana visible; ver [pendientes](#pendientes)).
Auditoría de Daniel Chet del 2026-11-08 sobre `fix/proyecto3-final-compliance`,
contra el enunciado oficial *Proyecto Fase 3 — Generación de Código* (PDF del curso).

## Registro del cierre

| Dato | Resultado |
|---|---|
| Commit de integración evaluado | `9d495ad` (rama `fix/proyecto3-final-compliance`, sobre la entrega del bloque 4) |
| Entregas individuales y revisiones | Bloque 1 APROBADO; bloque 2 implementado (dictamen pendiente); bloques 3 y 4 APROBADOS el 2026-11-08 |
| Python / Java / MARS y SHA-256 del JAR | Python 3.14.7; Java 21 (Temurin); MARS 4.5, `ac340b676ba2b62246b9df77e62f81ad4447bcfd329ab539716bcd09950b7096` |
| Comandos de aceptación y logs | `py -3.14 -m pytest tests --require-mars -q` → **1267 passed** en 544 s, 0 skips; `git diff --check` limpio |
| Regresión previa y suite MIPS requerida | Base del bloque 4 en checkout limpio: 1263 passed; `tests/mips --require-mars`: 328 passed |
| Ensayo visible de IDE y MARS | PENDIENTE (las pruebas Qt corren offscreen) |
| Checkout limpio repetido por otro integrante | Hecho por Daniel: `git worktree` sin `output/` ni cachés → 1263 passed |
| Incidencias y dictamen final | INC-B3-01, INC-B3-02, INC-B3-03 e INC-B4-01 cerradas; sin incidencias abiertas en el código |

## Cumplimiento del enunciado

| Requisito del PDF | Implementación | Evidencia ejecutada | Estado |
|---|---|---|---|
| Saltos hacia y desde procedimientos | `jal`/`jalr` al entrar y `jr $ra` en un epílogo único (`src/mips/calls.py`) | ABI-01, CALL-01 a CALL-04, `CALL-recursion.cps` (recursión directa y mutua) | Cumple |
| Preservar la memoria con `$sp` | Prólogo `sp -= F`, epílogo `sp = fp + F`; el caller reserva y libera `8*n`; `raise` restaura `$sp` | Canarios de `$sp`/`$fp` en llamadas y excepciones | Cumple |
| Parámetros, dirección y valor de retorno en el registro de activación | Encabezado de 32 bytes: `ra` 0, `fp` anterior 8, enlace de acceso 16, valor de retorno 24; argumentos en `fp + F + 8*i` | `--show-mips-layout` y pestaña Frames MIPS; CALL-02 (6 argumentos) | Cumple |
| `getReg()` asigna registros libres | `RegisterAllocator.getReg` (`src/mips/registers.py`): registro libre, víctima no fijada, respaldo de la víctima modificada | REG-01 a REG-03 | Cumple |
| Uso de `$t` y `$s` | `$t0`–`$t7` para temporales y globales; `$s0`–`$s7` para parámetros y locales de cada procedimiento, guardados y restaurados por el callee (agregado en `9d495ad`) | REG-04 y canarios de `$s0`–`$s7` | Cumple |
| Uso de la pila sin registros libres | Derrames a slots del frame y recargas; las pruebas también corren con bancos de 2 registros | REG-02, `REG-presion.cps` (29 derrames, 49 recargas) | Cumple |
| Generar MIPS desde el TAC | `generate_mips` con un handler por opcode; nunca entrega ensamblador parcial | PIPE-01, PIPE-02, `test_opcode_catalog_is_complete` | Cumple |
| Ejecutar en un simulador y validar | MARS 4.5 desde la API, la CLI (`--run-mips`) y el IDE (F6, cancelable) | SIM-01, E2E-01: 24 fixtures con oráculo escrito a mano, API = CLI = IDE | Cumple |
| Entrada `.cps`; salida ASM y reporte de errores | `--emit-mips`, IDE con la pestaña MIPS y exportación; diagnósticos por fase con ubicación y códigos 0/1/2 | CLI-01, CLI-02, IDE-01, IDE-02 | Cumple |
| Flujo ANTLR → semántica → TAC → MIPS → simulador | `compile_to_mips` reutiliza las fases 1 y 2 sin cambios | ACC-05, `test_pipe_01_every_accepted_project_program_generates_mips` | Cumple |
| Batería de casos exitosos y fallidos | `tests/cps/mips/{validos,runtime,invalidos}` y 1267 pruebas automáticas | E2E-01, `--require-mars` sin skips | Cumple |
| IDE para escribir y compilar | `py -3.14 -m src.main`: editor, TAC, MIPS, frames, ejecución y exportación | IDE-01 a IDE-04 (offscreen) | Cumple; falta el ensayo visible |
| Commits individuales, sin commits compartidos | Fase 3: Daniel (Poposit) 14, Nadissa 5, Dulce 5, Nelson 4; autor = committer y sin `Co-Authored-By` | `git shortlog -sn 82756c9..9d495ad` | Cumple |
| Documentación de arquitectura y de ejecución | `ARQUITECTURA.md`, `DISENO_MIPS.md`, README principal (instalación de MARS con hash, CLI, IDE y pruebas) | DOC-01 | Cumple |

Rúbrica: llamadas y retornos (20), asignación de registros (20) y MIPS funcional con
pruebas (60) quedan vinculados a comportamiento ejecutado en MARS, no solo a diseño.

## Pendientes

1. **Dictamen del bloque 2 (Nadissa).** Su entrega sigue en "revisión pendiente". Sus
   pruebas pasan dentro de las 1267, pero falta registrar el dictamen.
2. **Demo en ventana visible.** Otro integrante debe seguir el
   [ensayo de la demostración](entrega-bloque4-nelson.md#ensayo-de-la-demostración)
   en Windows con la interfaz visible.
3. **Rama a evaluar.** Igual que en la fase 2, la revisión vive en
   `fix/proyecto3-final-compliance` y se integra en `feature/proyecto3-mips`; `main` sigue
   en el Proyecto 1.
4. Observación: el nombre de Git de Daniel es `Poposit`; conviene mencionarlo al
   presentar los aportes.

## Lista de aceptación del equipo

- [ ] Puertas de Daniel, Nadissa, Dulce y Nelson aprobadas sobre commits identificados (falta la de Nadissa).
- [x] Todos los IDs y ACC-01 a ACC-08 con evidencia localizable.
- [x] Rúbrica 20/20/60 vinculada a comportamiento ejecutado, no solo diseño.
- [x] Todos los opcodes y capacidades acordadas cubiertos; ninguna omisión silenciosa.
- [x] Llamadas, recursión, registros vivos y spills verificados con canarios.
- [x] Closures, herencia local y excepciones entre frames ejecutadas en MARS.
- [x] Casos de error con fase/código correctos y sin salidas parciales aceptadas.
- [x] CLI/IDE coherentes, exportación segura y resultados vigentes por revisión.
- [x] MARS requerido disponible; cero skips de integración en aceptación.
- [x] Suite previa limpia y gramática/perfil preservados.
- [ ] Instalación y demostración repetidas desde checkout limpio (checkout hecho; falta la demo visible).
- [x] Aportes individuales, autorización de cuatro integrantes y enunciado disponibles.

## Interpretación del dictamen

Marcar listo solo cuando no queden bloqueos dentro del alcance acordado.
Las observaciones cosméticas pueden quedar identificadas como tales, con
responsable y justificación. Cualquier cambio funcional posterior invalida
las pruebas afectadas hasta repetirlas.

La revisión inicial de la base del Proyecto 2 tuvo 903 pruebas aprobadas y
dos fallos del fixture local de listas; consta en [PLAN.md](PLAN.md). No
trasladar ese resultado a la nueva fase ni afirmar una suite limpia sin repetirla.

La corrección `f2f2a15` restauró el fixture con autorización del propietario.
La base volvió a pasar 905 pruebas antes del desarrollo. El código completo
del bloque 1 hasta `f580a20` pasó 985 pruebas, incluidas las de MARS, como
registra su entrega.

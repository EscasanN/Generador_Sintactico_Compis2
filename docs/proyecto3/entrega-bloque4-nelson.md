# Entrega de IDE, CLI, batería integral y entrega reproducible de Nelson Escalante

## Identificación

| Campo | Valor |
|---|---|
| Bloque e integrante | Bloque 4 — Nelson Escalante |
| Fecha y rama | 2026-11-07 — `feature/proyecto3-04-ide-delivery` |
| Commit base aceptado | `f3843e2` (entrega del bloque 3 de Dulce, revisión de su puerta pendiente) |
| Commits de implementación | `5fe50d7` (CLI y `mips_consumer`), `06ea5ea` (IDE), `493fd1f` (fixtures y pruebas); la documentación va en el commit siguiente |
| Commit implementado y revisado | **PENDIENTE** (lo registra el revisor al integrar; ver puerta) |
| Revisor de la puerta | **PENDIENTE** |
| Python / Java / MARS y SHA-256 JAR | Python 3.14.3; Java 26.0.1 (Oracle, lanzador `javapath`); MARS 4.5, 4 169 142 bytes, `ac340b676ba2b62246b9df77e62f81ad4447bcfd329ab539716bcd09950b7096` (igual al de los bloques 1 a 3) |

## Cambios y contratos

El bloque presenta y coordina el backend existente; no genera ni modifica
ensamblador. Matriz: [MATRIZ_BLOQUE4_NELSON.md](MATRIZ_BLOQUE4_NELSON.md).

| Archivo | Contenido |
|---|---|
| `src/main.py` | CLI: `--emit-mips [RUTA]`, `--show-mips-layout`, `--run-mips`; validación de combinaciones; reporte por fase; códigos 0/1/2. Las opciones TAC no cambian. |
| `src/mips_consumer.py` (nuevo, sin Qt) | `write_text_safely` (temporal + `os.replace`), `default_mars_config` (`MARS_JAR` o `output/mips/tools/Mars4_5.jar`, sin descargas), `execution_exit_code`, `physical_layout`/`describe_physical_layout` (ranuras con nombre) y `CancellableMarsRun`. |
| `src/gui/mips_results.py` (nuevo) | `MipsView` (búsqueda, copia, exportación atómica), `PhysicalLayoutPanel` (área `$gp` y frames físicos, rotulados aparte del registro abstracto TAC) y `ExecutionPanel`. |
| `src/gui/app.py` | `CompilationWorker` genera también MIPS; `ExecutionWorker` ejecuta con cancelación; acciones Ejecutar (`F6`), Cancelar (`Ctrl+.`) y Exportar MIPS (`Ctrl+Shift+E`); invalidación por revisión y cierre seguro (`shutdown_workers`). |
| `tests/test_main_mips_cli.py` | CLI-01 y CLI-02 (25 casos, MARS real). |
| `tests/gui/test_mips_workflow.py` | IDE-01 a IDE-04 (8 casos, workers y MARS reales). |
| `tests/mips/test_mips_fixtures.py` | E2E-01: inventario y paridad API/CLI/IDE con oráculo (25 casos). |
| `tests/cps/mips/` | 7 programas de la demostración con oráculos JSON escritos a mano. |
| `README.md`, `docs/proyecto3/*` | Instalación de MARS, comandos comprobados, estado y matrices. |

### Contratos de los consumidores

* **Compilación.** La CLI usa `compile_to_mips`. El IDE compone
  `compile_compiscript(..., grammar_path, profile_path)` + `generate_mips` con la
  misma regla (el backend solo corre si el TAC es aceptado), porque la ventana
  conserva su gramática y perfil configurables. `test_e2e_01_consumers_agree_with_api_and_oracle`
  comprueba que ambos producen el mismo ensamblador que la API en los 24 fixtures.
* **Canales.** Si `--emit-tac` o `--emit-mips` no tienen ruta, stdout contiene
  solo ese texto y el reporte va a stderr. `--run-mips` exige rutas explícitas.
* **Archivos.** Cada archivo se escribe solo si su fase fue aceptada, por
  temporal en la misma carpeta y `os.replace`. Un rechazo, una cancelación del
  diálogo o un error de E/S conserva el archivo anterior.
* **Ejecución.** `CancellableMarsRun` repite las dos invocaciones de `run_mars`
  (`a` y luego `sm N`, con `nc me ae2 se3 db`) y su clasificación (reutiliza
  `_failure` y `_text` del simulador). Agrega el estado `cancelled`
  (`MIPS-CANCELLED`) y termina el **árbol** de procesos (`taskkill /T` en
  Windows, grupo de procesos en POSIX).
* **Códigos.** 0 éxito; 1 rechazo de cualquier fase o error del programa
  (`runtime_error`, `simulation_error`); 2 E/S, opciones, `tool_error`,
  `assembly_error`, `timeout`, `step_limit` o `cancelled`.
* **Revisiones.** Cada resultado de compilación y de ejecución lleva la revisión
  del documento que lo inició. Editar, abrir o crear documento limpia ASM,
  frames y ejecución, deshabilita Ejecutar/Exportar y cancela un MARS activo; una
  señal de una revisión anterior se descarta.

### Desviaciones y decisiones registradas

| Tema | Decisión | Cobertura |
|---|---|---|
| Ejecutor propio en vez de `run_mips` | `run_mars` no permite cancelar y su timeout no termina el `java.exe` real cuando `java` es el lanzador `javapath` (INC-B4-01). CLI e IDE usan `CancellableMarsRun`; no se modificó el módulo de Daniel. | `test_e2e_01_consumers_agree_with_api_and_oracle`, `test_cli_02_…timeout…`, `test_ide_03_…cancel…` |
| IDE sin `compile_to_mips` | Composición explícita para respetar `grammar_path`/`profile_path` de la ventana. | paridad de ensamblador en los 24 fixtures |
| `simulation_error` → 1 | Un trap de MARS durante el programa es un fallo del programa, no de la herramienta. | `execution_exit_code` |
| Nombres de los fixtures | Los de la guía (`REG-presion`, `CALL-recursion`…); `OBJ-herencia-local` no choca con `OBJ-03-herencia-local` de Dulce. | inventarios de Dulce y de este bloque |

## Evidencia por requisito

Comando de cada fila: `py -3.14 -m pytest <prueba> --require-mars -q` con
`MARS_JAR` apuntando al JAR verificado.

| ID | Requisito | Responsable | Prueba positiva y fixture | Negativa o invariante | Esperado | Resultado real | Estado |
|---|---|---|---|---|---|---|---|
| IDE-01 | Compilar contenido actual | Nelson | `test_ide_01_unsaved_buffer` (`DEMO-completa`) | el archivo cambia en disco y el buffer no se sustituye | ASM idéntico al de la API para el buffer; frames `global [main]`, `fn_factorial [proc_fn_factorial]` con `ra`, `fp anterior`, enlace de acceso y valor de retorno | aprobado | IMPLEMENTADO |
| IDE-02 | Exportar con seguridad | Nelson | `test_ide_02_export` | diálogo cancelado no escribe; `os.replace` falla y `previo\n` queda intacto sin temporales; `ERROR-tipos` deshabilita exportar | bytes UTF-8/LF iguales a la API; búsqueda `proc_fn_factorial`; copia = vista | aprobado | IMPLEMENTADO |
| IDE-03 | Ejecutar sin bloquear | Nelson | `test_ide_03_execution_lifecycle` (`DEMO-completa`) | `…cancel_terminates_java_without_freezing` (bucle infinito, `_run_execution` < 1 s, Qt procesa eventos, cancelar termina en < 15 s); `…timeout_and_missing_tool` (`timeout`, `tool_error`, `RuntimeError: DIV_ZERO`); `…close_during_execution_stops_java` | salida `30 120 11 12 75 Ana tiene saldo 14 3 capturado DIV_ZERO fin`; estado `success` | aprobado; 0 procesos `java.exe` tras la suite | IMPLEMENTADO |
| IDE-04 | Revisión de documento | Nelson | `test_ide_04_stale_results` | compilación y ejecución de una revisión anterior descartadas; abrir otro archivo invalida; `…signal_cannot_revive_old_output` | tras recompilar, `otro.cps` imprime `5` | aprobado | IMPLEMENTADO |
| CLI-01 | Opciones y flujos | Nelson | `test_cli_01_options_*` (stdout solo ASM, ruta UTF-8/LF, `--run-mips` con rutas, `--show-mips-layout`, TAC sin cambios) | 8 combinaciones inválidas, incluida `--run-mips --emit-tac --emit-mips`; fallo de E/S conserva el archivo | código 0; salida del programa exacta | aprobado (15 casos) | IMPLEMENTADO |
| CLI-02 | Estados y canales | Nelson | `test_cli_02_exit_and_channels_*` | rechazo léxico/semántico/TAC conserva `.asm` (1); `RuntimeError: DIV_ZERO` (1); límite de pasos (2); timeout 2 s (2); JAR ausente (2); fuente ilegible (2) | códigos y marcadores exactos | aprobado (10 casos) | IMPLEMENTADO |
| E2E-01 | Batería integral | Nelson | `test_e2e_01_consumers_agree_with_api_and_oracle` (24 fixtures) | `test_e2e_01_fixture_inventory`: cabecera, IDs de las cuatro matrices, oráculo 1:1, programas de la demo, esquema del JSON | ASM API = CLI = IDE; salida CLI e IDE = oráculo; código 0/1 | aprobado (25 casos) | IMPLEMENTADO |
| DOC-01 | Instalación y defensa | Nelson | [Instalación y ensayo](#instalación-y-ensayo-desde-checkout-limpio), README | copia sin `output/` ni cachés | suite completa en la copia | ver sección | IMPLEMENTADO (falta repetición por otro integrante) |
| GIT-01 | Autoría verificable | Equipo | commits propios de este bloque | sin commits compartidos | historial por integrante | ver puerta | PENDIENTE (equipo) |

### Oráculos de los programas de la demostración

Escritos a mano antes de ejecutar; los siete coincidieron con MARS en la primera ejecución.

| Fixture | Esperado | Qué demuestra |
|---|---|---|
| `validos/DEMO-completa` | `30 120 11 12 75 Ana tiene saldo 14 3 capturado DIV_ZERO fin` | integral |
| `validos/REG-presion` | `55 190 -5 20` | 23 derrames, llamada con valores vivos |
| `validos/CALL-recursion` | `120 55 true true 21 25` | recursión directa y mutua, 6 argumentos |
| `validos/ENV-escape` | `1 2 2 101 3 101 40` | closure escapada, hermanas comparten, creadores independientes, dos niveles |
| `validos/OBJ-herencia-local` | `7 30 23 23` | instancias, herencia local, método ligado escapado |
| `validos/EXC-captura` | `capturado INDEX_OUT_OF_RANGE -1 modulo DIV_ZERO continua` | error tres frames abajo |
| `invalidos/ERROR-tipos` | `REJECT semantic`, sin ejecución | sin TAC ni ASM |

## Regresión y reproducción

| Comprobación | Resultado |
|---|---|
| Base `f3843e2`, `tests --require-mars` | 1198 passed en 166 s, 0 skips |
| Puerta del bloque: `tests/gui/test_mips_workflow.py tests/test_main_mips_cli.py tests/mips --require-mars` | **358 passed** en 268 s, 0 skips |
| Regresión completa `tests --require-mars` | **1263 passed** en 293 s, 0 skips, 0 fallos (65 pruebas nuevas: 58 del bloque y 7 casos de `test_pipe_01_end_to_end` por los fixtures nuevos) |
| `git diff --check` | sin errores |

Log local: `output/qa/proyecto3/block4-acceptance.xml` (ignorado por Git).

## Instalación y ensayo desde checkout limpio

Comandos verificados en Windows 11 (PowerShell):

```powershell
git clone --branch feature/proyecto3-04-ide-delivery https://github.com/EscasanN/Generador_Sintactico_Compis2.git
cd Generador_Sintactico_Compis2
py -3.14 -m pip install -r requirements.txt
New-Item -ItemType Directory -Force output/mips/tools | Out-Null
Invoke-WebRequest https://raw.githubusercontent.com/dpetersanderson/dpetersanderson.github.io/master/Mars4_5.jar -OutFile output/mips/tools/Mars4_5.jar
(Get-FileHash output/mips/tools/Mars4_5.jar -Algorithm SHA256).Hash   # AC340B67…7096
$env:MARS_JAR = (Resolve-Path output/mips/tools/Mars4_5.jar).Path
py -3.14 -m pytest tests --require-mars -q
py -3.14 -m src.main --cps tests/cps/mips/validos/DEMO-completa.cps --run-mips
py -3.14 -m src.main
```

Ensayo realizado por Nelson: copia con solo los archivos versionados (`git ls-files`,
sin `output/` ni cachés de ANTLR) y `MARS_JAR` al JAR verificado (ANTLR se descargó y generó de cero): **1263 passed** en
294 s, 0 skips; `--run-mips` sobre `DEMO-completa` terminó en `success` y no quedó
ningún proceso `java.exe`.

**Pendiente:** que otro integrante repita este checkout limpio y la demostración
en una ventana visible de Windows. Las pruebas Qt de este bloque corren en modo
offscreen y no sustituyen ese ensayo humano.

### Ensayo de la demostración

1. `py -3.14 -m src.main`, abrir `tests/cps/mips/validos/DEMO-completa.cps`,
   **Compilar**: pestañas **Código TAC**, **MIPS** (estadísticas y derrames) y
   **Frames MIPS** (encabezado `$ra`/`$fp`/enlace de acceso/valor de retorno).
   **Ejecutar en MARS** muestra la salida del oráculo. **Exportar .asm…** y
   ejecutar el archivo con `java -jar %MARS_JAR% nc me sm db ae2 se3 1000000 demo.asm`.
2. `REG-presion.cps`: estadística de derrames/recargas y `55 190 -5 20`.
3. `CALL-recursion.cps`: en **Frames MIPS**, `fn_sumarSeis` con seis argumentos
   entrantes en `48($fp)`…`88($fp)` (por encima del frame de 48 bytes).
4. `ENV-escape.cps` y `OBJ-herencia-local.cps`: closures y métodos ligados.
5. `EXC-captura.cps`: error tres frames abajo capturado y ejecución continua.
6. `ERROR-tipos.cps`: rechazo semántico; MIPS vacío, Exportar deshabilitado.
   Volver al válido sin guardar y comprobar que solo se exporta el actual.
7. Cancelar: escribir `let x: integer = 0; while (true) { x = x + 1; }`,
   compilar y ejecutar; la ventana sigue respondiendo y **Cancelar** termina MARS.
   Con el límite por defecto, MARS termina antes con `step_limit`.
8. CLI: `--emit-mips salida.asm --show-mips-layout --run-mips` sobre `DEMO-completa`.

## Incidencias

| ID | Gravedad | Descripción | Responsable | Estado |
|---|---|---|---|---|
| INC-B4-01 | Media | `src/mips/simulator.py::run_mars` usa `subprocess.run(timeout=…)`. En Windows, `java` suele ser el lanzador `C:\Program Files\Common Files\Oracle\Java\javapath\java.exe`, que crea el `java.exe` real como hijo. Al expirar el timeout se mata solo el lanzador; el hijo conserva los pipes y `run_mars` espera hasta que MARS termina. Reproducción: bucle infinito, `MarsConfig(jar, timeout=2, step_limit=10**9)` → el resultado `timeout` llegó a los **190 s**. Los consumidores del bloque 4 no dependen de ello (`CancellableMarsRun` termina el árbol). | Daniel (simulador) | Abierta, reportada; mitigada en CLI/IDE |
| INC-B4-02 | Baja | Durante el desarrollo, una prueba manual previa a la corrección dejó un MARS huérfano (`sm 1000000000`) que terminó solo; no quedaron procesos tras las suites (comprobado con `Get-CimInstance Win32_Process`). | Nelson | Cerrada |
| INC-B3-01 | Media | `for` sin condición con `break` seguido de más código sigue rechazado por el TAC (Proyecto 2). Los fixtures del bloque 4 no lo usan. | Propietario del TAC | Abierta (heredada) |

## Puerta de aceptación

- [x] Todos los IDs propios tienen evidencia ejecutada (GIT-01 depende del equipo).
- [x] MARS real ejecutó los casos exigidos sin skips por dependencia.
- [x] Regresión acumulada y formato del diff correctos.
- [x] Contratos utilizables sin implementar pendientes de otros bloques (INC-B4-01 queda para Daniel).
- [ ] Otro integrante reprodujo la puerta, el checkout limpio y la demo visible, y registró dictamen.
- [ ] Commits de autoría individual identificables y commit final registrado arriba.

Dictamen: **PENDIENTE**. Cambiar a APROBADO solo con fecha, commit y revisor.

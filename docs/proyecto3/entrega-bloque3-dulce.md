# Entrega de runtime, memoria compuesta, excepciones y pipeline de Dulce Ambrosio

Fecha: 2026-11-07. Rama: `feature/proyecto3-03-runtime-pipeline`, creada sobre la rama
del bloque 2 (`feature/proyecto3-02-calls-environments`).
Base de partida: `7bf0c56` (bloque 2 de Nadissa con las incidencias del bloque 1 corregidas).
Commit implementado y revisado: **PENDIENTE** (se registra al integrar; ver puerta).

## Resultado y alcance

El bloque completa el backend: cadenas, impresión de todos los tipos, listas, objetos,
herencia (también local), errores runtime con manejadores y desenrollado entre frames,
el registro integral de handlers (`generate_mips`) y la API `.cps` → MIPS
(`compile_to_mips`). Cada opcode del enum `OpCode` tiene exactamente un handler.
Se verifica con programas `.cps` reales ejecutados en MARS, IR manual para los casos
internos imposibles desde fuente y fixtures con oráculos escritos a mano.

No incluye la CLI ni la GUI (bloque 4). No modifica ningún módulo de los bloques 1 y 2.

## Preparación y reproducción

| Campo | Valor |
|---|---|
| Python / Java | 3.12.10 (entorno virtual `output/venv`, ignorado por Git) / OpenJDK 17.0.20.1 (Temurin) |
| MARS | 4.5, JAR oficial `raw.githubusercontent.com/dpetersanderson/dpetersanderson.github.io/master/Mars4_5.jar` |
| Tamaño y SHA-256 del JAR | 4 169 142 bytes; `ac340b676ba2b62246b9df77e62f81ad4447bcfd329ab539716bcd09950b7096` (idéntico a los bloques 1 y 2) |
| Ubicación | `output/mips/tools/Mars4_5.jar`, ignorado por Git |

```powershell
python -m venv output\venv
output\venv\Scripts\python.exe -m pip install -r requirements.txt
$env:MARS_JAR = (Resolve-Path 'output/mips/tools/Mars4_5.jar').Path
output\venv\Scripts\python.exe -m pytest tests/mips/test_runtime.py tests/mips/test_mips_lists.py tests/mips/test_mips_objects.py tests/mips/test_exceptions.py tests/mips/test_mips_pipeline.py --require-mars -q
output\venv\Scripts\python.exe -m pytest tests/mips --require-mars -q
output\venv\Scripts\python.exe -m pytest tests --require-mars -q --junitxml=output/mips/block3-acceptance.xml
git diff --check
```

Uso de la API:

```python
from src.mips.models import MarsConfig
from src.mips.pipeline import compile_to_mips, run_mips

compilacion = compile_to_mips(open('programa.cps', encoding='utf-8').read(), 'programa.cps')
if compilacion.accepted:
    print(compilacion.mips.assembly)                          # ensamblador completo
    ejecucion = run_mips(compilacion, MarsConfig('output/mips/tools/Mars4_5.jar'))
    print(ejecucion.status, ejecucion.returncode, ejecucion.stdout)
else:
    print(compilacion.failed_stage)                            # syntax, semantic, codegen o mips
```

## Cambios y contratos

Módulos propios (`src/mips/`): `runtime.py`, `lists.py`, `objects.py`, `exceptions.py`,
`generator.py`, `pipeline.py`.
Pruebas (`tests/mips/`): `test_runtime.py`, `test_mips_lists.py`, `test_mips_objects.py`,
`test_exceptions.py`, `test_mips_pipeline.py` y el arnés `pipeline_harness.py`.
Fixtures: `tests/cps/mips/{validos,runtime,invalidos}` con oráculos JSON en `esperados/`.
Matriz: [MATRIZ_BLOQUE3_DULCE.md](MATRIZ_BLOQUE3_DULCE.md).

### APIs

| API | Uso |
|---|---|
| `generate_mips(intermediate_result, *, gpr_count=8, fpr_count=5)` | `IntermediateCodeResult` aceptado → `MipsGenerationResult` (`assembly`, `diagnostics`, `layouts` = `PhysicalLayoutPlan`, `statistics`). Rechazo: diagnósticos con ubicación y ensamblador vacío. |
| `compile_to_mips(source, source_path=None)` | Ejecuta `compile_compiscript` sin cambios; solo llama al backend si el frontend y el TAC aceptan. No ensambla ni ejecuta. |
| `run_mips(compilation, config)` | Ejecución explícita de una compilación aceptada mediante `run_mars`; una rechazada lanza `ValueError`. |
| `MipsProgramEmitter(plan, runtime=None, *, gpr_count, fpr_count)` | Composición integral (subclase de `ProgramEmitter` de Nadissa): agrega `ListHandler`, `ObjectHandler`, `ExceptionHandler`, `RuntimeRegisterAllocator` por unidad y emite los helpers tras la última unidad. `handler_for(opcode)` y `check_coverage(program)`. |
| `CompiscriptRuntime` | Subclase de `BaseRuntime`: `string_literal`, `print_value`, `emit_string`, `error`, `handler_head`, `error_payload`, `emit_helpers`. |

### Representación y runtime

* **Cadena**: longitud en bytes UTF-8 en offset 0, padding hasta 8, contenido desde 8.
  Los literales se emiten como `.byte` numéricos en `.data` (un objeto por texto) y
  admiten cualquier Unicode; `null` es 0 y nunca es `""`.
* `+` de cadenas comprueba `null` (→ `NULL_ACCESS`) y llama a `concat`, que reserva un
  objeto nuevo. `==`/`!=` llaman a `equals` (contenido, `null == null`); los órdenes
  llaman a `compare` (bytes UTF-8 sin signo, `null` → `NULL_ACCESS`).
* Los helpers (`concat`, `equals`, `compare`, `raise`) son procedimientos hoja de la
  misma ABI con frame vacío: argumentos en slots de 8 bytes en `sp + 8*i`, resultado en
  `$v0`. Solo usan `$a0`–`$a3`, `$v0`/`$v1`, `$t8`/`$t9`; nunca `$sp`, `$fp`, `$s*` ni
  registros asignables. Se emiten una vez, después de la última unidad, y solo si se usan.
* **print**: números, booleanos y `null` con el runtime de Daniel; cadenas con syscall 15
  (descriptor 1, longitud explícita), así UTF-8 llega intacto; listas, objetos y
  callables imprimen `[list]`, `[object]` y `[function]`; una referencia nula imprime `null`.
* **Lista**: longitud en offset 0, elementos desde 8 con stride 8 y ancho de su tipo
  (`lbu/sb`, `lw/sw`, `l.d/s.d`). Antes de cada acceso: `null` → `NULL_ACCESS` y
  `0 <= i < longitud` con una comparación sin signo (también rechaza negativos) →
  `INDEX_OUT_OF_RANGE`.
* **Objeto**: región del tamaño exacto de su `ClassLayout` (offsets abstractos y slots de
  entornos preservados). `OBJECT_NEW` no ejecuta inicializadores: el constructor del TAC
  lo hace, base primero. `FIELD_GET`/`FIELD_SET` comprueban `null` y validan el offset en
  el layout de la clase del receptor por identidad (clases homónimas no se confunden).
* **Excepciones**: `TRY_BEGIN` empuja un registro de 40 bytes (enlace 0, catch 8, `$sp` a
  restaurar 16, `$fp` 24, `$ra` 32) y lo pone como cabeza de una cadena guardada en una
  palabra global. `TRY_END` lo retira una vez. `error` deja el payload (cadena con el
  código) en `$a0` y salta a `raise`, que retira la cabeza, restaura `$sp`/`$fp`/`$ra`,
  guarda el payload en una palabra global y salta al catch; sin manejador imprime
  `RuntimeError: CODIGO` y termina con syscall 17 y código 1. `CATCH` copia el payload.

### Desviaciones y decisiones registradas

| Tema | Decisión | Cobertura |
|---|---|---|
| Literales de cadena en cualquier operando (`PARAM`, `LIST_SET`, `FIELD_SET`, `ENV_SET`, `RETURN`) | `RuntimeRegisterAllocator` amplía `_constant` de Daniel: un literal es `la reg, etiqueta`. No hace falta el `loader` de Nadissa; cierra INC-B2-02 sin tocar sus módulos. | `test_str_01_*`, fixtures `STR-01`, `LIST-01` |
| Etiqueta del catch | `ExceptionHandler` resuelve la etiqueta con `ScalarLowerer._label` del mismo emisor (la que marca `LABEL`). Es un método interno del bloque 1; conviene publicarlo si se refactoriza. | `test_exc_*` |
| `null + "x"` y `null < "x"` | No especificado en el diseño: se decide `NULL_ACCESS` (no se desreferencia ni se trata como `""`). | `test_str_01_null_strings_are_never_dereferenced` |
| Cadena impresa | syscall 15 en lugar de syscall 4 para conservar UTF-8 y longitud explícita (diseño). | `test_str_01_strings` (Unicode) |
| Nombres de pruebas | `test_mips_lists.py` y `test_mips_objects.py` en lugar de `test_lists.py`/`test_objects.py`: ya existen en `tests/codegen/` y pytest no admite módulos homónimos. | inventario de pytest |
| Inventario semántico | `tests/semantic/test_cps_programs.py` excluye `tests/cps/mips/` igual que `tests/cps/codegen/`: tiene su propio inventario en `test_pipe_01_fixture_inventory`. | ambos inventarios |
| Aprobación | No se marca APROBADO sin revisor ni commit (ver puerta). | — |

## Evidencia por requisito

Todas las pruebas están en `tests/mips/` y se ejecutaron con MARS obligatorio.

| ID | Pruebas principales (positiva / negativa o invariante) | Esperado | Estado |
|---|---|---|---|
| STR-01 | `test_runtime.py::test_str_01_strings`, `…null_is_not_the_empty_string`, `…null_strings_are_never_dereferenced` (3), `…literals_are_numeric_utf8_bytes_with_explicit_length`, `…helpers_do_not_clobber_live_values` (8 y 2 registros), `…helpers_preserve_stack_and_saved_registers`, `…print_dispatches_by_type_with_stable_markers`, `…operations_undefined_for_strings_are_rejected_with_location`, `…print_of_an_unresolved_type_is_rejected`; fixtures `STR-01-cadenas`, `STR-01-concatenar-nulo` | `Compiscript`; contenido igual con direcciones distintas; `"Z" < "a"`, `"é" > "z"`; `canción ñandú €`; `null` ≠ `""`; `null + "x"` → `RuntimeError: NULL_ACCESS`; canario de `$sp`/`$fp`/`$s0`–`$s7` = 1 | IMPLEMENTADO |
| LIST-01 | `test_mips_lists.py::test_list_01_operations` (8 y 2 registros), `…bounds_are_checked_before_reading` (-1, 3, 2), `…null_lists_raise_null_access` (store, load, foreach), `…store_out_of_range_never_writes_a_neighbour`, `…invalid_reservation_size_is_rejected`, `…element_representation_must_match_the_list`; fixtures `LIST-01-listas`, `EXC-01-indice-sin-manejador` | suma 6; vacía 0 vueltas; dobles 3.75; matriz y alias 40; cadenas `ba`; objetos 15; 20 elementos 370; -1 y longitud → `INDEX_OUT_OF_RANGE`; nula → `NULL_ACCESS`; `LIST_NEW -1` → `MIPS-INVALID-ADDRESS` con ubicación | IMPLEMENTADO |
| OBJ-01 | `test_mips_objects.py::test_obj_01_instances` (8 y 2 registros), `…null_receivers_raise_null_access` (lectura, escritura, método), `…incoherent_offsets_and_sizes_are_rejected`; fixtures `OBJ-01-instancias`, `EXC-01-nulo-sin-manejador` | 9 y 30 independientes; campos sin inicializar en cero/false; constructor implícito 42/`ok`; offset fuera de clase → `MIPS-INVALID-ADDRESS`; tamaño incoherente → `MIPS-INVALID-IR`; clase inexistente → `MIPS-MISSING-LAYOUT` | IMPLEMENTADO |
| OBJ-02 | `test_obj_02_inheritance`, `test_obj_02_homonymous_classes_never_share_a_layout`; fixture `OBJ-02-herencia` | inicializadores `ABC` (base primero); `A`/`B`/`soy A` por resolución estática del TAC; dos `Caja` con layouts y tipos distintos: 6, `dos`, 6 | IMPLEMENTADO |
| OBJ-03 | `test_obj_03_local_inheritance` (8 y 2 registros); fixture `OBJ-03-herencia-local` | inicializador heredado lee la `x` de la base (5), no la de la derivada (1000): 1005; método ligado escapado ve la celda actualizada: 6; contadores ligados 5, 10, 7 | IMPLEMENTADO |
| EXC-01 | `test_exceptions.py::test_exc_01_errors`, `…without_handler_prints_code_and_exits_with_one` (5); fixtures `EXC-01-*` | `DIV_ZERO` (entero, módulo, doble, resto doble), `INDEX_OUT_OF_RANGE`, `NULL_ACCESS`; sin manejador: `RuntimeError: CODIGO`, código 1, sin excepción de MARS | IMPLEMENTADO |
| EXC-02 | `test_exc_02_unwind` (8 y 2 registros), `…unwinding_restores_stack_frame_and_saved_registers`, `…handler_head_is_restored_after_each_catch`; fixtures `EXC-02-desenrollado`, `EXC-02-catch-que-falla` | error 7 frames abajo capturado y el programa sigue (600); catch que falla llega al exterior; 100 capturas sin fuga; canario = 1; tras cada catch no queda manejador viejo | IMPLEMENTADO |
| EXC-03 | `test_exc_03_transfers`, `…register_pressure_inside_catch` (8 y 2 registros), `…records_are_pushed_and_retired_symmetrically`; fixtures `EXC-03-salidas-protegidas`, `EXC-01-division-sin-manejador` | `return`/`break`/`continue` y try anidados retiran solo lo suyo (3, 53, `exterior vigente`, 7) y el último error queda sin manejador; un `addiu -40` por `TRY_BEGIN` y un `+40` por cada `TRY_END` del TAC | IMPLEMENTADO |
| PIPE-01 | `test_mips_pipeline.py::test_pipe_01_end_to_end` (17 fixtures), `…fixture_inventory`, `…every_accepted_project_program_generates_mips` (todos los válidos y con warnings de fases previas), `…rejected_phases_never_call_the_backend`, `…frontend_result_is_preserved_and_nothing_is_executed`, `…run_mips_executes_only_accepted_compilations` | stdout y código exactos por fixture; cortocircuito 1, ternario, 4 formas de for, while, do-while, switch con caída y discriminante una vez, fib 55, 6 argumentos 21, `-7/2 = -3`, `-7%2 = -1`; syntax/semantic/codegen → `mips is None` sin TAC | IMPLEMENTADO |
| PIPE-02 | `test_opcode_catalog_is_complete`, `test_pipe_02_rejections`, `…invalid_inputs_are_rejected_without_assembly`, `…compilation_result_keeps_stages` | cada `OpCode` del enum real con un handler; sin handler → `MIPS-UNSUPPORTED-OPCODE` con ubicación; externo → `MIPS-UNKNOWN-EXTERNAL`; tipo no resoluble → `MIPS-UNRESOLVED-TYPE`; TAC rechazado, sin layouts o IR malformada → rechazo sin ASM | IMPLEMENTADO |

## Regresión y reproducción

| Comprobación | Resultado |
|---|---|
| Base (`7bf0c56`), Python 3.12.10, `tests --require-mars` | 1069 passed, 3 failed en 190.6 s (los tres por falta del ejecutable `dot` de Graphviz; ver INC-B3-02) |
| Puerta del bloque (5 archivos nuevos), `--require-mars` | **126 passed** en 70 s, sin skips |
| `tests/mips --require-mars` (bloques 1, 2 y 3, árbol final) | **293 passed** en 195.8 s, sin skips |
| `tests --require-mars` con el bloque | **1195 passed, 3 failed** en 244.1 s: los mismos 3 fallos de Graphviz de la base; 0 regresiones, 0 skips, 126 pruebas nuevas |
| `git diff --check` | Sin errores |

Se usó el árbol de trabajo de la autora, no un checkout limpio. El log local está en
`output/mips/block3-acceptance.xml` (ignorado) y se resume aquí.

### Verificación por mutación

Se introdujeron, de uno en uno, 14 defectos deliberados y se ejecutó la puerta del bloque:
`TRY_END` sin liberar el registro, `raise` sin retirar el manejador, `raise` sin restaurar
`$sp`, registro que guarda `$sp` después de empujarse, catch que lee la cabeza en vez del
payload, comprobación de índice con signo, stride de 4 bytes, listas y campos sin
comprobación de nulo, igualdad de cadenas por identidad, `concat` que olvida el segundo
operando, cadenas impresas con syscall 4, `OBJECT_NEW` sin validar tamaño y orden de bytes
con signo. Las pruebas detectaron **13 de 14**. El superviviente (`slt` en lugar de `sltu`
tras `lbu`) es un mutante equivalente: los bytes se cargan sin signo (0–255), igual que
`lb` seguido de `sltu`; el defecto real (`lb` + `slt`) sí se detecta en `test_str_01_strings`.

## Incidencias

| ID | Gravedad | Descripción | Responsable | Estado |
|---|---|---|---|---|
| INC-B3-01 | Media | **Defecto del TAC del Proyecto 2** (`src/codegen/control_flow.py`): en un `for` **sin condición** (`for (;;)` o `for (; ; act)`), un `break` dentro de un `if` sale sin liberar el temporal de la condición del `if` (solo se libera en el camino que cae a `if_end`). Si después hay más código que reutiliza temporales en la misma unidad, `IRVerifier` rechaza un programa válido con `IR-TEMP-COLLISION` (fase `codegen`). Reproducción mínima: `let n: integer = 0; for (;;) { n = n + 1; if (n == 4) { break; } } let w: integer = 0; while (w < 2) { w = w + 1; }`. `while (true)` y los `for` con condición no lo presentan. No es del backend MIPS: el programa no llega a él. | Propietario del TAC del Proyecto 2 | Abierta, reportada; el fixture `PIPE-01-control-y-funciones` aísla esos `for` en funciones |
| INC-B3-02 | Baja (entorno) | En este equipo no está instalado el ejecutable `dot` de Graphviz: `test_main_window_is_configured_only_for_compiscript`, `test_ide_04_and_05_compile_reports_categorized_diagnostics_with_location` y `test_ide_07_parse_tree_has_both_image_and_navigable_views` fallan con `ExecutableNotFound` igual que en la base, sin relación con este bloque. | Equipo (instalación) | Abierta; preexistente |
| INC-B3-03 | Baja (entorno) | El equipo tiene Python 3.12.10 y Java 17; la documentación usa 3.14 y Java 21. La suite completa pasa en este entorno; repetir en 3.14 al integrar. | Revisor de la puerta | Abierta |
| INC-B2-02 | Media | Literales de cadena en `PARAM` (bloque 2). | Dulce | Cerrada: `RuntimeRegisterAllocator` los materializa en cualquier operando |

## Limitaciones

El heap no se libera (diseño). Las cadenas Unicode se imprimen por syscall 15; la salida
gráfica de MARS con `-Dfile.encoding=UTF-8` no se ensayó en este bloque (la ejecución por
terminal sí). Un `for` sin condición con `break` seguido de más código sigue rechazado por
el TAC (INC-B3-01).

## Puerta de aceptación

- [x] Todos los IDs propios tienen evidencia ejecutada (estado IMPLEMENTADO).
- [x] MARS real ejecutó los casos exigidos sin skips por dependencia.
- [x] Regresión acumulada y formato del diff correctos (salvo INC-B3-02, preexistente y de entorno).
- [x] Contratos utilizables por el siguiente bloque sin implementar pendientes propios.
- [ ] Otro integrante reprodujo la puerta y registró dictamen.
- [ ] Commits de autoría individual identificables y commit final registrado arriba.

Dictamen: **PENDIENTE**. Cambiar a APROBADO solo con fecha, commit y revisor.

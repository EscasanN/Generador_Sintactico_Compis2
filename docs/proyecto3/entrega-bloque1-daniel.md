# Entrega del núcleo MIPS de Daniel Chet

Fecha: 2026-11-04. Rama: `feature/proyecto3-01-mips-core`.
Base de planificación: `82756c9`. Corrección de regresión: `f2f2a15`.
Contratos/emisor/simulador: `ec7c3fd`. Implementación completa revisada: `f580a20`.

## Resultado y alcance

El bloque implementa emisor MIPS32, memoria tipada, registros enteros/dobles,
derrames, operaciones escalares, control de flujo y adaptador de MARS. Se
verifica con IR manual y con un ejemplo ejecutable independiente de las pruebas.

Nadissa recibe contratos y componentes reales; debe implementar los layouts
de símbolos/frames del compilador, llamadas y entornos de su bloque. El pipeline
`.cps` → MIPS completo, runtime compuesto y GUI siguen pendientes en sus bloques.
No se presenta el ejemplo manual como compilación completa de Compiscript.

## Preparación y reproducción

Entorno verificado: Python 3.14.7, Java 21, MARS 4.5 oficial.
El JAR permanece en `output/mips/tools/Mars4_5.jar`, ignorado por Git.

- Fuente utilizada: [JAR del repositorio oficial de Pete Sanderson](https://raw.githubusercontent.com/dpetersanderson/dpetersanderson.github.io/master/Mars4_5.jar).
- Tamaño: 4 169 142 bytes.
- SHA-256: `ac340b676ba2b62246b9df77e62f81ad4447bcfd329ab539716bcd09950b7096`.

Desde la raíz, instalar `requirements.txt`, disponer de Java y descargar el JAR
oficial a una ruta local. Definir `MARS_JAR` explícitamente; los tests también
reconocen la cache local anterior. No hay descargas al importar el backend.

```powershell
$env:MARS_JAR = (Resolve-Path 'output/mips/tools/Mars4_5.jar').Path
py -3.14 -m scripts.demo_mips_core --jar "$env:MARS_JAR" --output output/mips/demo.asm
py -3.14 -m pytest tests/mips --require-mars -q
py -3.14 -m pytest tests --require-mars -q --junitxml=output/mips/block1-acceptance.xml
git diff --check
```

La demo imprime `30` seguido de LF y exporta el ensamblador ejecutado. Usa
un resolver de tres slots y dos registros enteros. Su prueba lanza el módulo
en otro proceso: no importa helpers de `tests/`.

## Contratos que utiliza Nadissa

| Componente | API implementada y propiedad |
|---|---|
| `models` | `MachineLocation`, `LocationResolver`, `EmissionContext`, `CallEmitter`, `InstructionHandler`, resultados y configuración inmutables. |
| `MipsEmitter` | `mark`, `label`, `emit`, `branch`, `double`, `ascii`, `load`, `store`, `render`; valida duplicados y destinos de `branch`. |
| `RegisterAllocator` | `getReg`, `write`, `pin`, `unpin`, `flush`, `invalidate`, `release`, `location`; identidad temporal por procedimiento y lease. |
| `ScalarLowerer` | `supports`, `emit(instruction, context)` para composición; `lower(instructions, context)` verifica IR global aislada. |
| `BaseRuntime` | `allocate`, `print_value`, `error`, `exit`, `emit_string`; servicios inline que no dependen del emisor general de llamadas. |
| `run_mars` | Ensamblado previo y simulación, UTF-8/LF, timeout, límite de pasos y diagnósticos separados. |

### Ubicaciones y vida de temporales

Implementar `LocationResolver` con sus cuatro operaciones. `address_of` y
`temporary_slot` devuelven `MachineLocation` con base física, offset, tamaño
reservado y ancho de acceso. Bases admitidas: `$fp`, `$sp`, `$gp`; offsets
no negativos y alineados. Globals pueden ubicarse en una región basada en `$gp`.

El resolver es propietario de la pertenencia lease → procedimiento y del plan
de slots. Puede reutilizar un slot tras terminar una vida, incluso con otro
tipo, si reserva/alinea espacio suficiente. `validate_locations` se aplica a
reservas simultáneamente vivas, no a todas las vidas históricas superpuestas.

El allocator conserva el tipo por identidad incluso tras invalidar cachés.
Un temporal debe definirse por `write` o `getReg(..., mode='write')` antes de
leerse o liberarse. `release` descarta su estado; no debe volver a utilizarse
el mismo lease. Un nombre reciclado requiere lease nuevo. Los símbolos deben
conservar su identidad y tipo declarado, aunque otro scope reuse su nombre.

Para emitir: fijar fuentes mientras se obtienen registros, calcular el resultado
en scratch, liberar los pins y comprometerlo con `write`. Antes de llamadas o
entradas/salidas de bloques, ejecutar `flush`, retirar pins e `invalidate`.
No vaciar manualmente los diccionarios ni perder valores dirty.

### Reservas de registros y proveedores

Se asignan `$t0`–`$t7` y pares `$f2`–`$f11`; `$t8/$t9` son scratch.
Dobles usan scratch `$f14/$f15` y `$f16/$f17`. El módulo flotante reserva
también `$f18/$f19`, `$f20/$f21`, `$f22/$f23`, `$f24/$f25`. Ninguno pertenece
al banco asignable. `$s0`–`$s7` se dejan intactos. La ABI propia no promete ABI Linux.

`BaseRuntime.allocate` hace barrera de registros, reserva/limpia bytes y devuelve
el puntero en `$t8`. Debe consumirse o guardarse antes de otra emisión que use
scratch. `print_value` hace barrera e imprime entero, doble, booleano o nulo;
el runtime de Dulce extenderá impresión y datos compuestos.

`BaseRuntime.error` es un proveedor **no retornante**, llamado tras `flush`
en ambas rutas. Emite solo ASM con registros reservados: no debe cambiar los
descriptores del allocator, que también describen la rama de éxito. Dulce
puede emitir un salto a su manejador; el catch entra con caché de registros
vacía. No aplicar `invalidate` sobre fuentes pinned dentro de este callback.

`emit_string` recibe la instrucción y el contexto tras una barrera. Devuelve
True solo si emitió la operación completa; la implementación base devuelve
False y la traducción rechaza con diagnóstico. Una prueba ejecutada demuestra
la inyección de un proveedor de concatenación literal; no sustituye el runtime
general de cadenas que corresponde a Dulce.

### Validación y publicación

`ScalarLowerer.lower` valida un `IRProgram` global mediante `IRVerifier`.
Para cuerpos de procedimientos, el generador integral validará el programa
completo y llamará `emit` por instrucción con su contexto propio. El mismo
contexto debe mantener alineados `procedure` y `registers.procedure`.

Las operaciones no soportadas, tipos inconsistentes, literales malformados y
ubicaciones faltantes se rechazan. Si un handler lanza `MipsError`, descartar
esa emisión y construir un resultado rechazado sin ASM. Los errores incluyen
la ubicación de la instrucción cuando existe. `MipsCompilationResult` conserva
los estados previos y no admite MIPS sobre un frontend rechazado.

No usar `emit` para ocultar destinos de salto: `branch` registra la referencia
y agrega `nop`; `mark` define su destino. `double` usa patrones de bits de dos
palabras para soportar también NaN/inf en la memoria little-endian de MARS.

## Evidencia por requisito

Todas las pruebas referidas están en `tests/mips/`. La ejecución de puerta
es la suite completa con `--require-mars`; el registro final identifica su commit.

| ID | Pruebas principales | Resultado exigido y negativas comprobadas |
|---|---|---|
| CORE-01 | `test_core_01_deterministic_and_validated`, `test_core_01_assembles`, `test_handoff_example_exports_and_executes` | Dos emisiones iguales; ensamblado real; duplicados y destinos ausentes rechazados; demo imprime 30. |
| MEM-01 | `test_mem_01_typed_storage`, `test_mem_01_rejects_invalid_storage`, `test_mem_01_overlap` | Bytes sin signo, enteros, dobles y punteros preservados; padding vecino intacto; invalidez y solapamiento rechazados. |
| REG-01 | `test_reg_01_allocation_and_pinning`, `test_pinned_operands_are_not_silently_evicted` | Cálculo con dos registros produce 30; no se expulsa un operando pinned; no se invalida dirty sin guardar. |
| REG-02 | `test_reg_02_spill_and_reload`, `test_live_values_survive_successful_division` | Suma de doce valores produce 78 en ambos bancos; valores vivos alrededor de división producen 53. |
| REG-03 | `test_reg_03_temporary_leases`, `test_disjoint_leases_can_reuse_one_slot_with_different_types`, `test_foreign_lease_cannot_be_released`, `test_lease_cannot_change_type_after_definition` | Mismo nombre con leases distintos; slot compartido integer/double/integer produce 7, 2.5, 9; uso muerto, extranjero y cambio de tipo rechazados. |
| NUM-01 | `test_num_01_*`, `test_double_remainder_special_values`, `test_invalid_literal_has_located_backend_diagnostic` | Aritmética, comparaciones, cast, límites, NaN y signed zero; módulo con cociente mayor que int32 y divisor subnormal; cero controlado; entradas malformadas diagnosticadas. |
| FLOW-01 | `test_flow_01_joins_and_loops` | Bucle con dos registros produce suma 10 y contador 5; descriptores no cruzan la frontera sin respaldo. |
| SIM-01 | `test_sim_01_*`, `test_timeout_keeps_output_already_printed` | Distingue éxito, herramienta ausente, ensamblado inválido, trap, pasos y timeout; conserva el stdout parcial 30 al matar Java. |

Pruebas adicionales: dos reservas de heap distintas preservan canario 77,
memoria cero y valor vivo 41; se validan gates de resultados y diagnóstico
inmutable. Los oráculos son literales calculados independientemente del backend.

## Revisión y aceptación

Revisión técnica independiente requerida por `requesting-code-review`.
Los hallazgos de referencias nominales, extensión de cadenas, salida parcial,
literales inválidos, tipos de lease y validación de ubicaciones se reprodujeron
con pruebas y se corrigieron antes del cierre. La revisión no atribuye al bloque
llamadas, closures, layouts completos, excepciones ni compilación `.cps` → MIPS.

Resultado sobre el código de `f580a20`, antes de estos cambios documentales:

| Comprobación | Resultado |
|---|---|
| Base recuperada antes de implementar | 905 passed en 41.55 s. |
| Suite completa con `--require-mars` | **985 passed en 126.83 s**, sin skips. |
| Casos nuevos del bloque | **80**, incluidos dentro de la suite anterior. |
| `compileall` de backend, tests y demo | Sin errores. |
| `git diff --check` | Sin errores. |
| Ejemplo exportado/ejecutado por test en otro proceso | Salida `30` y código 0. |
| Revisión independiente | Sin hallazgos críticos o importantes pendientes; listo para cierre de puerta. |

La evidencia estructurada queda en `output/mips/block1-acceptance.xml` local;
estos comandos, resultados y commits versionados permiten repetirla aunque no
se distribuya el log. Las pruebas de Python ejecutaron Qt offscreen como parte
de la regresión previa; no se atribuye a esta entrega un ensayo humano del IDE.

**Puerta 1 aprobada.** Se entrega la rama para revisión e integración en
`feature/proyecto3-mips`. Nadissa debe crear su rama desde esa integración
aceptada; no desde el commit de planificación que carece de estos módulos.

## Incidencias tras la entrega

Nadissa Vela revisó el bloque sobre `74aa81f` y encontró estas incidencias, que no
bloqueaban la puerta. Se reabrió la puerta 1 y se corrigieron sobre la rama del
bloque 2, porque INC-B1-01 depende de INC-B2-04. Responsable: Daniel Chet.

| ID | Gravedad | Reproducción e impacto | Corrección y regresión |
|---|---|---|---|
| INC-B1-01 | Media (latente) | Un lease liberado en cada rama de un `if` se rechazaba con `MIPS-TEMPORARY-RELEASED`, aunque `IRVerifier` lo acepta. Ningún programa aceptado genera hoy ese patrón. | `ddabb25`: el contrato acepta el patrón y los liberados se olvidan solo en `LABEL`. `test_reg_03_lease_released_on_each_path_runs`, `test_reg_03_use_after_release_is_rejected_across_a_conditional_jump`, `test_abi_01_lease_released_on_each_path_keeps_its_value_in_mars` |
| INC-B1-02 | Media | `allocate` costaba 7 pasos de MARS por byte: una reserva de 160 KB agotaba el límite de 1 000 000 de pasos. Afectaba a las listas del bloque 3. | `e42b0c1`: limpieza por palabras dobles, 1 paso por byte. 800 KB terminan; 1 MB todavía agota el límite. `test_large_reservation_fits_the_default_step_limit`, `test_cleared_area_stays_inside_its_reservation` |
| INC-B1-03 | Baja | `MipsEmitter.ascii` duplicaba cadenas en `.data` y lanzaba `UnicodeEncodeError` con texto no ASCII. | `0cf3ab6`: caché propio y diagnóstico `MIPS-NON-ASCII`. `test_ascii_reuses_equal_strings`, `test_ascii_and_double_with_the_same_bytes_keep_separate_labels`, `test_non_ascii_text_is_a_backend_diagnostic` |
| INC-B1-04 | Baja | `ScalarLowerer._label` usaba `id()` del emisor como clave; un `id` reciclado podía devolver etiquetas de otro emisor. | `52ce06b`: la clave es el emisor. `test_labels_are_not_shared_when_an_emitter_id_is_recycled` |

Comprobaciones repetidas con Python 3.14.7 y MARS 4.5 sobre `52ce06b`:

| Comprobación | Resultado |
|---|---|
| `tests --require-mars` | **1072 passed**, sin skips (21 nuevas sobre las 1051 del bloque 2) |
| `compileall` de backend, tests y scripts | Sin errores |
| `git diff --check 59457cf 52ce06b` | Sin errores |
| `scripts.demo_mips_core` | Salida `30` y código 0 |

Queda pendiente que otro integrante reproduzca la puerta y registre el dictamen.

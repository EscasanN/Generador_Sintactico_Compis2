# Entrega de llamadas, entornos y closures de Nadissa Vela

Fecha: 2026-11-06. Rama: `feature/proyecto3-02-calls-environments`.
Base de partida: `74aa81f` (bloque 1 de Daniel aprobado, rama `feature/proyecto3-01-mips-core`).
Commit implementado y revisado: **PENDIENTE** (se registra al integrar; ver puerta).

## Resultado y alcance

El bloque implementa la ABI propia del compilador y todo lo que depende de ella:
frames físicos por procedimiento, paquete de argumentos, prólogo/epílogo y retorno
único, llamadas directas e indirectas, recursión, entornos de capturas en heap,
closures escapadas y métodos ligados. Se verifica con IR manual tipada ejecutada
en MARS y, además, con el IR y los layouts reales que produce el Proyecto 2.

No incluye cadenas, listas, objetos, excepciones, el pipeline `.cps` → MIPS ni la
GUI: son de los bloques 3 y 4. Las pruebas no dependen de módulos futuros.

## Preparación y reproducción

| Campo | Valor |
|---|---|
| Python / Java | **3.14.7** / 21.0.2 (el entorno documentado por Daniel); la suite también pasa con 3.11.3 |
| MARS | 4.5, JAR oficial obtenido clonando `github.com/dpetersanderson/dpetersanderson.github.io` |
| Tamaño y SHA-256 del JAR | 4 169 142 bytes; `ac340b676ba2b62246b9df77e62f81ad4447bcfd329ab539716bcd09950b7096` (idéntico al registrado por Daniel) |
| Comprobaciones del JAR | hash coincidente; análisis de Windows Defender sin amenazas; sin `ProcessBuilder`, `Runtime.exec` ni sockets en sus clases (solo `java.net.URL` en la GUI de MARS); única `.bat` es su script de construcción |
| Ubicación | `output/mips/tools/Mars4_5.jar`, ignorado por Git |

Con Python 3.14 en un entorno virtual aparte (`output/venv314`, ignorado por Git; el 3.14 se
instaló en paralelo con el instalador oficial firmado de python.org, sin tocar el 3.11):

```powershell
py -3.14 -m venv output\venv314
output\venv314\Scripts\python.exe -m pip install -r requirements.txt
$env:MARS_JAR = (Resolve-Path 'output/mips/tools/Mars4_5.jar').Path
python -m pytest tests/mips/test_call_layout.py tests/mips/test_calls.py tests/mips/test_environments.py --require-mars -q
python -m pytest tests/mips --require-mars -q
python -m pytest tests --require-mars -q --junitxml=output/mips/block2-acceptance.xml
git diff --check
```

## Cambios y contratos

Módulos propios (`src/mips/`): `layout.py`, `calls.py`, `environments.py`.
Pruebas (`tests/mips/`): `test_call_layout.py`, `test_calls.py`, `test_environments.py`,
`test_call_integration.py` y el arnés `abi_harness.py`.
Matriz: [MATRIZ_BLOQUE2_NADISSA.md](MATRIZ_BLOQUE2_NADISSA.md).

### Frame físico y ABI

```text
$fp + 0   ra            $fp + 8   fp anterior (enlace de control)
$fp + 16  enlace de acceso (el `env` recibido)   $fp + 24  respaldo del valor devuelto
$fp + 32… locales, celdas de temporales (reutilizables), área de staging de PARAM
$fp + F   argumento 0   $fp + F + 8*i   argumento i   (ocultos primero: this, env)
```

* Caller: cada `PARAM` copia su valor **en ese momento** a un slot de staging del
  frame; `CALL` hace `sp = sp - 8n`, copia el paquete a `sp + 8*i`, `jal`/`jalr` y
  `sp = sp + 8n`. Un `RELEASE` entre `PARAM` y `CALL` no afecta al paquete.
* Callee: `sp = sp - F`, guarda `ra` y el `fp` anterior antes de `fp = sp`, limpia el
  frame (los locales sin inicializar valen cero) y guarda el `env` en el enlace de
  acceso. Todo `RETURN` carga `$v0`/`$f0`, escribe el respaldo y salta a **un** epílogo.
* `$s0`–`$s7` jamás se tocan. Antes de salir o llamar se escriben los valores
  modificados (incluidos globales) y se invalidan los descriptores. Tras una llamada
  se libera `A` con `addiu`, nunca con `move $sp, $fp`, para respetar registros de
  manejadores de excepción que el bloque 3 coloque en el stack.
* Estáticos: región `.data` apuntada por `$gp` (el punto de entrada ejecuta `la $gp`).
* Llamada indirecta: lee la máscara del descriptor en ejecución y salta a una de
  cuatro variantes (0 nada, 1 `env`, 2 `this`, 3 ambos) que inserta los ocultos antes
  de los explícitos. Descriptor nulo → `NULL_ACCESS`; máscara fuera de 0–3 → `INVALID_CALLABLE`.
* Entornos: `ENV_NEW` en heap con `BaseRuntime.allocate`. `(profundidad, offset)` sigue los
  enlaces con el `EnvironmentLayout` de **cada** ancestro (el padre léxico se deriva de los
  scopes del Proyecto 2 o se inyecta explícitamente); el enlace de control no interviene.
* Descriptor de callable de 32 bytes: código 0, entorno 8, receptor 16, máscara 24.

### APIs

| API | Uso |
|---|---|
| `PhysicalLayoutPlan.build(program, layouts, parents=None)` | Planifica todos los procedimientos; implementa `LocationResolver` (`address_of`, `temporary_slot`, `field_offset`, `environment_access`). |
| `CallingConvention(plan, loader=None)` | `CallEmitter` (`emit_call`, `emit_return`) e `InstructionHandler` de `PARAM`, `CALL`, `CLOSURE_CALL`, `RETURN`; `begin_program`, `begin_procedure`, `end_procedure`. |
| `EnvironmentHandler(plan)` | `InstructionHandler` de `ENV_NEW`, `ENV_SET`, `ENV_GET`, `CLOSURE`, `METHOD_REF`. |
| `allocate_descriptor`, `fill_descriptor` | Constructores reutilizables de descriptores (para métodos ligados de objetos). |
| `ProgramEmitter(plan, runtime=None, extra_handlers=(), loader=None)` | Composición de referencia: un único handler por opcode, verifica el IR, emite punto de entrada, global y procedimientos. Dulce puede usarla o sustituirla. |

### Para el bloque 3 (Dulce)

* Registrar sus handlers con `extra_handlers`; un opcode con dos dueños falla.
* `CALL print` delega en `context.runtime.print_value(context, operando)`; su runtime
  extiende la impresión a cadenas y marcadores.
* Un `PARAM` con literal de cadena necesita su proveedor: se pasa como `loader`
  (devuelve el registro con la dirección, o `None` para el comportamiento normal).
  Sin él se rechaza con `MIPS-UNRESOLVED-TYPE`; nunca se simula.
* Los helpers que usen `jal` deben seguir la misma ABI (guardar `ra`/`fp`).
* Constructores y métodos reciben `this`/`env` como `PARAM` explícitos en `CALL`;
  `CLOSURE_CALL` los agrega desde el descriptor. No se duplican.

### Desviaciones y decisiones registradas

| Tema | Decisión | Cobertura |
|---|---|---|
| `environment_access` | Devuelve `EnvironmentAccess(links, offset, target)`; el diseño no fijaba el tipo. | `test_env_01_links_come_from_each_ancestor_layout` |
| Máscara inválida | Error de ejecución `INVALID_CALLABLE` (el diseño exige rechazarla, sin nombrar el código). | `test_env_02_null_and_corrupt_callables_report_errors` |
| Tamaño de frame | Máximo 0x6000 bytes: los inmediatos de MIPS son de 16 bits con signo. | `test_abi_01_frame_size_is_bounded_by_the_offset_range` |
| Celdas de temporales | Se reutilizan solo tras `RELEASE`; un lease sin liberar vive hasta el final y uno que entra a un bucle se extiende a su salto de retorno. | `test_abi_01_temporary_cells_*`, `test_abi_01_lease_alive_into_a_loop_keeps_its_cell` |
| Aprobación | No se marca APROBADO sin revisor ni commit (ver puerta). | — |

## Evidencia por requisito

Todas las pruebas están en `tests/mips/` y se ejecutaron con MARS obligatorio.

| ID | Pruebas principales (positiva / negativa o invariante) | Esperado | Estado |
|---|---|---|---|
| ABI-01 | `test_call_layout.py::test_abi_01_frame_mapping`; `…rejects_broken_frames`, `…rejects_foreign_symbols_leases_and_links`, `…rejects_inconsistent_inputs`, `…incoming_formula_with_many_arguments`, `…large_frames_are_cleared_and_never_leak_stale_values`, `…contracts_and_opcode_ownership`; `test_call_integration.py::test_every_valid_project2_program_has_a_complete_physical_plan` (22 programas) | Locales sombreados en celdas distintas y alineadas; argumento `i` en `fp+F+8i` con 11 argumentos; símbolo ajeno, solapamiento, tamaño insuficiente y enlace inexistente rechazados | IMPLEMENTADO |
| CALL-01 | `test_calls.py::test_call_01_arguments` (0, 1 y 6 argumentos: 7, 42, 21, 123456), `…mixed_integer_double_boolean_reference`, `…captured_once_and_survive_release`, `…rejects_bad_signatures`, `…argument_loader_hook…`; `test_environments.py::test_direct_calls_carry_their_hidden_parameters_explicitly` | Orden y tipos preservados; aridad, representación, `PARAM` incompleto y destino desconocido rechazados | IMPLEMENTADO |
| CALL-02 | `test_call_02_returns` (void, 42, 2.5, referencia, booleano, todos los caminos), `…rejects_incompatible_returns` | Cada retorno vuelve al caller; `void` con destino y mezcla doble/palabra rechazados | IMPLEMENTADO |
| CALL-03 | `test_call_03_preservation` (30, 3.75, 1510, 7, 0, 42, canario, 7, 1) con 2 registros | `f()+g()` y valores vivos con derrames; `$sp`, `$fp` y `$s0`–`$s7` idénticos; globales escritos antes, dentro y después de llamadas | IMPLEMENTADO |
| CALL-04 | `test_call_04_recursion` (5! = 120, fib 8 = 21, par/impar mutuos, suma 200 = 20100), `…with_scarce_registers`; programas reales de Compiscript | Activaciones sin locales compartidos; retorno correcto | IMPLEMENTADO |
| ENV-01 | `test_environments.py::test_env_01_lexical_links` (profundidades 0, 1, 2 con padres a distintos offsets), `…links_come_from_each_ancestor_layout`, `…rejects_unresolvable_access`, `…double_boolean_and_reference_cells` | Lecturas y escrituras llegan a la declaración correcta; sin enlace de control ni offset universal | IMPLEMENTADO |
| ENV-02 | `test_env_02_escape` (1, 2, 3 tras limpiar el stack; creador nuevo: 1), `…escape_through_two_levels` (510), `…null_and_corrupt_callables_report_errors`, `…rejects_inconsistent_closures` | Contadores independientes y vivos tras el creador; nulo → `RuntimeError: NULL_ACCESS`, máscara 7 → `INVALID_CALLABLE` | IMPLEMENTADO |
| ENV-03 | `test_env_03_shared_capture` (1, 2, 1, 2) | Hermanas comparten la celda; la que solo reenvía el entorno funciona; cada invocación del creador es independiente | IMPLEMENTADO |
| METHOD-01 | `test_method_01_bound_call` (105, 1005, 12, 1026, 1032), `…rejects_invalid_callables`, `test_indirect_calls_with_doubles_booleans_and_both_hidden_kinds` | La misma variable pasa por máscaras 0, 1, 2 y 3; receptor y entorno sobreviven al creador; ocultos no se duplican; receptor nulo → `NULL_ACCESS` | IMPLEMENTADO |

Además: `test_call_integration.py` compila `.cps` reales y los ejecuta en MARS
(anidadas + recursión: 26 y 120; closures escapadas: 1, 2, 101, 3; firmas mixtas;
hermanas: 12), comprueba que los opcodes de otros bloques se rechazan en vez de
ignorarse y que cada programa válido del Proyecto 2 tiene plan físico completo.

## Regresión y reproducción

| Comprobación | Resultado |
|---|---|
| Base (bloque 1 aprobado) | 985 pruebas |
| Puerta del bloque, Python 3.14.7 | **36 passed** en 43.7 s |
| `tests/mips --require-mars`, Python 3.14.7 | **145 passed** en 155.1 s, sin skips |
| `tests --require-mars`, Python 3.14.7 | **1050 passed** en 211.6 s, 0 fallos, 0 errores, 0 skips (65 nuevas) |
| Los mismos tres comandos, Python 3.11.3 | 36, 145 y 1050 passed (24.4 s, 92.6 s y 114.3 s) |
| `compileall`, `git diff --check` | Sin errores |

Se usó el árbol de trabajo del autor, no un checkout limpio. Los logs locales están en
`output/mips/block2-acceptance.xml` (ignorado) y se resumen aquí.

### Verificación por mutación

Se introdujeron 21 defectos deliberados (epílogo sin restaurar `fp`/`ra`/`sp`, sin limpiar
frames, sin escribir globales al retornar, sin liberar el paquete, ocultos intercambiados o
en el slot equivocado, máscara fija, receptor en el slot del entorno, offset de enlace
universal, celdas reutilizadas en vida, etc.). Las pruebas detectaron **21 de 21**. Tres
supervivientes iniciales revelaron pruebas débiles y se corrigieron: frames de distinto
tamaño que no compartían direcciones, valores simétricos que no distinguían `this` de
`env`, y `print` con destino de resultado.

## Incidencias

| ID | Gravedad | Descripción | Estado |
|---|---|---|---|
| INC-B2-01 | Alta (durante el desarrollo) | La llamada indirecta con máscara 3 caía en la variante de máscara 0 (faltaba el salto). La detectó METHOD-01 en MARS. | Corregida y cubierta |
| INC-B2-02 | Media | El allocator de Daniel rechaza literales de cadena en `PARAM`; su materialización pertenece al bloque 3. | Punto de extensión `loader` y prueba; pendiente su proveedor real |
| INC-B2-03 | Baja | El equipo solo tenía Python 3.11 y la documentación exige 3.14. | Cerrada: 3.14.7 instalado y suite completa verde en ambas versiones |

## Limitaciones

Los frames de más de 24 KB (0x6000 bytes) se rechazan; el heap no se libera (diseño); la estimación
de padres léxicos requiere los scopes del Proyecto 2 o un mapa explícito.

## Puerta de aceptación

- [x] Todos los IDs propios tienen evidencia ejecutada (estado IMPLEMENTADO).
- [x] MARS real ejecutó los casos exigidos sin skips por dependencia.
- [x] Regresión acumulada y formato del diff correctos.
- [x] Contratos utilizables por el siguiente bloque sin implementar pendientes propios.
- [ ] Otro integrante reprodujo la puerta y registró dictamen.
- [ ] Commits de autoría individual identificables y commit final registrado arriba.

Dictamen: **PENDIENTE**. Cambiar a APROBADO solo con fecha, commit y revisor.

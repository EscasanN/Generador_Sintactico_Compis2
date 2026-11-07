# Matriz del bloque 3 de Dulce Ambrosio

Responsable: Dulce Ambrosio. Estado: **IMPLEMENTADO** en todas las filas; la puerta
queda **pendiente de revisión independiente** y del commit final
(ver [la entrega](entrega-bloque3-dulce.md)).
Dependencia: bloque 2 implementado (revisado por Dulce antes de desarrollar).
Rúbrica principal: MIPS funcional y pruebas (60 puntos).
Pruebas dentro de `tests/mips/`; fixtures dentro de `tests/cps/mips/`.

| ID | Requisito | Caso positivo y esperado | Caso negativo o invariante | Prueba | Estado |
|---|---|---|---|---|---|
| STR-01 | Cadenas y salida | Concatenar `"Compi" + "script"` imprime `Compiscript`; igualdad por contenido, orden permitido, vacío y Unicode. | Direcciones distintas con mismo texto comparan igual; `null` no se trata como cadena vacía ni se desreferencia. | `test_runtime.py::test_str_01_strings` (+ `test_str_01_*`) | IMPLEMENTADO |
| LIST-01 | Listas completas | Lista vacía, enteros, dobles, referencias, anidación y `foreach`; `[1,2,3]` suma 6 tras recorrido. | Índices -1 y longitud, acceso nulo y tamaño de reserva inválido dan error previsto, no trap arbitrario. | `test_mips_lists.py::test_list_01_operations` (+ `test_list_01_*`) | IMPLEMENTADO |
| OBJ-01 | Construcción y miembros | Constructores explícitos/implícitos, campos y `this`; dos objetos retienen valores independientes. | Acceso nulo controlado y offset/descriptor IR incoherente rechazado. | `test_mips_objects.py::test_obj_01_instances` (+ `test_obj_01_*`) | IMPLEMENTADO |
| OBJ-02 | Herencia nominal | Campos base/derivados e inicializadores en orden base primero; métodos usan resolución del TAC. | Dos clases homónimas no comparten layout; el backend no introduce despacho dinámico ajeno al IR. | `test_mips_objects.py::test_obj_02_inheritance`, `test_obj_02_homonymous_classes_never_share_a_layout` | IMPLEMENTADO |
| OBJ-03 | Herencia local con entornos | Base y derivada de ámbitos distintos conservan capturas; construcción más anidada y método ligado funcionan. | Inicializador heredado usa entorno de su clase base, no el de la derivada o el llamador. | `test_mips_objects.py::test_obj_03_local_inheritance` | IMPLEMENTADO |
| EXC-01 | Error y catch | División/módulo cero, índice inválido y acceso nulo llegan al catch activo con código esperado. | Sin manejador imprime `RuntimeError: CODIGO` y termina en 1; no aceptar cualquier trap de MARS. | `test_exceptions.py::test_exc_01_errors`, `test_exc_01_without_handler_prints_code_and_exits_with_one` | IMPLEMENTADO |
| EXC-02 | Desenrollado entre frames | Error desde llamada anidada se captura en caller y continúa después del catch. | Stack, frame, payload y cabeza del manejador se restauran; catch que falla llega al manejador exterior. | `test_exceptions.py::test_exc_02_unwind`, `test_exc_02_unwinding_restores_stack_frame_and_saved_registers`, `test_exc_02_handler_head_is_restored_after_each_catch` | IMPLEMENTADO |
| EXC-03 | Salidas protegidas | `return`, `break`, `continue` y try anidados retiran solo sus manejadores. | No queda handler de frame terminado ni se retira dos veces; presión de registros en catch. | `test_exceptions.py::test_exc_03_transfers`, `test_exc_03_register_pressure_inside_catch`, `test_exc_03_records_are_pushed_and_retired_symmetrically` | IMPLEMENTADO |
| PIPE-01 | Compilar `.cps` y preservar efectos | Programas por dominio, cortocircuito, ternario, todos los ciclos, switch, funciones, objetos y listas ejecutan su salida esperada. | Errores léxicos/sintácticos/semánticos/TAC impiden llamar al backend y no dejan ASM parcial; warnings no bloquean. | `test_mips_pipeline.py::test_pipe_01_end_to_end` (17 fixtures), `test_pipe_01_*` | IMPLEMENTADO |
| PIPE-02 | Cobertura y contratos | Enum entero de opcodes cubierto; `print` usa tipo correcto; cero diagnósticos en casos válidos. | Opcode, externo o tipo/rol no resoluble se rechaza con ubicación disponible. | `test_mips_pipeline.py::test_opcode_catalog_is_complete`; `test_pipe_02_rejections` (+ `test_pipe_02_*`) | IMPLEMENTADO |

Los archivos `test_lists.py` y `test_objects.py` previstos se llaman `test_mips_lists.py`
y `test_mips_objects.py`: `tests/codegen/` ya tiene módulos con esos nombres y pytest no
admite dos módulos de prueba homónimos sin paquetes.

## Evidencia y comando de puerta

```powershell
py -3.14 -m pytest tests/mips --require-mars -q
py -3.14 -m pytest tests -q
```

El segundo comando comprueba regresión general, pero no reemplaza el primero:
la aceptación MIPS exige el simulador. Todos los programas de fixtures declaran
esperado de compilación, ejecución y stdout; ver [la guía](GUIA_PRUEBAS_Y_PRESENTACION.md).
Resultados y reproducción en [la entrega](entrega-bloque3-dulce.md).

## Handoff obligatorio

- [x] `generate_mips` y `compile_to_mips` completos, con resultados inmutables.
- [x] Registro de handlers exhaustivo y runtime sin etiquetas externas desconocidas.
- [x] Fixtures por dominio con oráculos explícitos y versiones de pruebas.
- [x] Métodos ligados reales, herencia local y errores entre frames ejecutados.
- [x] Comparación del catálogo con `OpCode`, incluyendo cualquier opcode agregado desde la planificación.
- [ ] Registro por ID con el commit final en [la entrega](entrega-bloque3-dulce.md): faltan commit y revisor.

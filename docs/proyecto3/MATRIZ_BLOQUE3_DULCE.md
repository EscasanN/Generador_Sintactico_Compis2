# Matriz del bloque 3 de Dulce Ambrosio

Responsable: Dulce Ambrosio. Estado: **PENDIENTE** en todas las filas.
Dependencia: bloque 2 aprobado. Rúbrica principal: MIPS funcional y pruebas (60 puntos).
Pruebas previstas dentro de `tests/mips/`; fixtures dentro de `tests/cps/mips/`.

| ID | Requisito | Caso positivo y esperado | Caso negativo o invariante | Prueba prevista | Estado |
|---|---|---|---|---|---|
| STR-01 | Cadenas y salida | Concatenar `"Compi" + "script"` imprime `Compiscript`; igualdad por contenido, orden permitido, vacío y Unicode. | Direcciones distintas con mismo texto comparan igual; `null` no se trata como cadena vacía ni se desreferencia. | `test_runtime.py::test_str_01_strings` | PENDIENTE |
| LIST-01 | Listas completas | Lista vacía, enteros, dobles, referencias, anidación y `foreach`; `[1,2,3]` suma 6 tras recorrido. | Índices -1 y longitud, acceso nulo y tamaño de reserva inválido dan error previsto, no trap arbitrario. | `test_lists.py::test_list_01_operations` | PENDIENTE |
| OBJ-01 | Construcción y miembros | Constructores explícitos/implícitos, campos y `this`; dos objetos retienen valores independientes. | Acceso nulo controlado y offset/descriptor IR incoherente rechazado. | `test_objects.py::test_obj_01_instances` | PENDIENTE |
| OBJ-02 | Herencia nominal | Campos base/derivados e inicializadores en orden base primero; métodos usan resolución del TAC. | Dos clases homónimas no comparten layout; el backend no introduce despacho dinámico ajeno al IR. | `test_objects.py::test_obj_02_inheritance` | PENDIENTE |
| OBJ-03 | Herencia local con entornos | Base y derivada de ámbitos distintos conservan capturas; construcción más anidada y método ligado funcionan. | Inicializador heredado usa entorno de su clase base, no el de la derivada o el llamador. | `test_objects.py::test_obj_03_local_inheritance` | PENDIENTE |
| EXC-01 | Error y catch | División/módulo cero, índice inválido y acceso nulo llegan al catch activo con código esperado. | Sin manejador imprime `RuntimeError: CODIGO` y termina en 1; no aceptar cualquier trap de MARS. | `test_exceptions.py::test_exc_01_errors` | PENDIENTE |
| EXC-02 | Desenrollado entre frames | Error desde llamada anidada se captura en caller y continúa después del catch. | Stack, frame, payload y cabeza del manejador se restauran; catch que falla llega al manejador exterior. | `test_exceptions.py::test_exc_02_unwind` | PENDIENTE |
| EXC-03 | Salidas protegidas | `return`, `break`, `continue` y try anidados retiran solo sus manejadores. | No queda handler de frame terminado ni se retira dos veces; presión de registros en catch. | `test_exceptions.py::test_exc_03_transfers` | PENDIENTE |
| PIPE-01 | Compilar `.cps` y preservar efectos | Programas por dominio, cortocircuito, ternario, todos los ciclos, switch, funciones, objetos y listas ejecutan su salida esperada. | Errores léxicos/sintácticos/semánticos/TAC impiden llamar al backend y no dejan ASM parcial; warnings no bloquean. | `test_mips_pipeline.py::test_pipe_01_end_to_end` | PENDIENTE |
| PIPE-02 | Cobertura y contratos | Enum entero de opcodes cubierto; `print` usa tipo correcto; cero diagnósticos en casos válidos. | Opcode, externo o tipo/rol no resoluble se rechaza con ubicación disponible. | `test_mips_pipeline.py::test_opcode_catalog_is_complete`; `test_pipe_02_rejections` | PENDIENTE |

## Evidencia y comando de puerta

```powershell
py -3.14 -m pytest tests/mips --require-mars -q
py -3.14 -m pytest tests -q
```

El segundo comando comprueba regresión general, pero no reemplaza el primero:
la aceptación MIPS exige el simulador. Todos los programas de fixtures deben
declarar esperado de compilación, ejecución y stdout; ver [la guía](GUIA_PRUEBAS_Y_PRESENTACION.md).

## Handoff obligatorio

- `generate_mips` y `compile_to_mips` completos, con resultados inmutables.
- Registro de handlers exhaustivo y runtime sin etiquetas externas desconocidas.
- Fixtures por dominio con oráculos explícitos y versiones de pruebas.
- Métodos ligados reales, herencia local y errores entre frames ejecutados.
- Comparación del catálogo con `OpCode`, incluyendo cualquier opcode agregado desde la planificación.
- Registro por ID y commit en [la plantilla](PLANTILLA_ENTREGA_BLOQUE.md).

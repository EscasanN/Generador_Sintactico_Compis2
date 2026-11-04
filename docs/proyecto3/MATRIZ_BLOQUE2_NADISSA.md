# Matriz del bloque 2 de Nadissa Vela

Responsable: Nadissa Vela. Estado: **PENDIENTE** en todas las filas.
Dependencia: bloque 1 aprobado. Rúbrica principal: llamadas/retornos (20 puntos).
Pruebas previstas dentro de `tests/mips/`, usando IR manual tipada y MARS.

| ID | Requisito | Caso positivo y esperado | Caso negativo o invariante | Prueba prevista | Estado |
|---|---|---|---|---|---|
| ABI-01 | Layout físico completo | Frames de dos funciones con shadowing tienen direcciones distintas, alineación y slots completos. | Tamaño insuficiente, solapamiento, símbolo de otro frame o enlace inexistente se rechaza. | `test_call_layout.py::test_abi_01_frame_mapping` | PENDIENTE |
| CALL-01 | Paquete de argumentos | Cero, uno, seis argumentos y mezcla entero/doble/referencia llegan en orden; suma de 1 a 6 retorna 21. | Aridad o firma inválida y `PARAM` incompleto se rechazan; no reevaluar argumentos al llamar. | `test_calls.py::test_call_01_arguments` | PENDIENTE |
| CALL-02 | Retorno y epílogo | `void`, entero 42, doble 2.5 y referencia conservan valor; todos los caminos vuelven al caller. | Firma/representación incompatible rechazada; retorno no omite restauraciones. | `test_calls.py::test_call_02_returns` | PENDIENTE |
| CALL-03 | Preservación entre llamadas | `f() + g()` y llamada con operandos vivos, enteros/dobles y spills, producen esperado; `$sp` antes/después idéntico. | Canarios en stack, `$fp` y `$s0`–`$s7` intactos; helpers no invalidan valores sin guardarlos. | `test_calls.py::test_call_03_preservation` | PENDIENTE |
| CALL-04 | Recursión directa y mutua | Factorial de 5 retorna 120; Fibonacci de 8 retorna 21; par/impar mutuos terminan correctamente. | Activaciones no comparten locales ni dirección de retorno. | `test_calls.py::test_call_04_recursion` | PENDIENTE |
| ENV-01 | Acceso léxico | Lectura/escritura a profundidad 0, 1 y 2 refleja los cambios en la declaración correcta. | No seguir enlace de control ni asumir un parent-offset universal. | `test_environments.py::test_env_01_lexical_links` | PENDIENTE |
| ENV-02 | Closure escapada | Contador retornado produce 1 y luego 2 tras terminar la función creadora. | No lee slots de un frame expirado; llamada indirecta nula produce interfaz de error. | `test_environments.py::test_env_02_escape` | PENDIENTE |
| ENV-03 | Compartir capturas y propagar dependencias | Dos hermanas modifican el mismo contador; hermana que solo llama otra recibe entorno necesario. | Dos invocaciones distintas del creador mantienen contadores independientes. | `test_environments.py::test_env_03_shared_capture` | PENDIENTE |
| METHOD-01 | Método ligado | Receptor y entorno capturado se conservan tras el creador; misma variable pasa de función global a método con entorno usando receptor de prueba. | Máscara runtime agrega `this`, luego `env`; no duplicar ocultos ni deducirlos del tipo fuente. Rechazar máscara inválida. | `test_environments.py::test_method_01_bound_call` | PENDIENTE |

## Evidencia y comando de puerta

Cada fila de llamadas/entornos debe tener ejecución real en MARS, además de
pruebas internas para IR inválida. El harness puede preparar receptores y
regiones de memoria: no requiere los constructores `.cps` del bloque 3.

```powershell
py -3.14 -m pytest tests/mips/test_call_layout.py tests/mips/test_calls.py tests/mips/test_environments.py --require-mars -q
py -3.14 -m pytest tests/mips --require-mars -q
```

Ejecutar regresión previa y completar el handoff. Un resultado numérico correcto
no basta para CALL-03: debe comprobarse restauración de stack/frame y registros.

## Handoff obligatorio

- ABI implementada y fórmulas verificadas con más de cuatro argumentos.
- Resolver real de símbolos, campos, entornos y temporales compatible con Daniel.
- Helpers de entornos y callable descriptors listos para reutilizar en objetos.
- Pruebas y evidencia sin depender de módulos futuros.
- Registro por ID y commit en [la plantilla](PLANTILLA_ENTREGA_BLOQUE.md).

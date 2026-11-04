# Matriz del bloque 1 de Daniel Chet

Responsable: Daniel Chet. Estado: **APROBADO** en todas las filas.
Dependencia: base del Proyecto 2 y diseño aprobado.
Rúbrica principal: registros/pila (20 puntos); soporte a MIPS funcional (60).

Las rutas siguientes son pruebas implementadas dentro de `tests/mips/`.
Cada prueba indicada debe cubrir todos los escenarios de su fila mediante
parametrización o casos adicionales; el nombre no reemplaza su implementación.

| ID | Requisito | Caso positivo y esperado | Caso negativo o invariante | Prueba prevista | Estado |
|---|---|---|---|---|---|
| CORE-01 | Emisor determinista y completo | Dos emisiones del mismo IR son idénticas; MARS ensambla `.data`, `.text` y `main`. | Duplicado o destino no resuelto genera diagnóstico, sin ensamblador aceptado. | `test_emitter.py::test_core_01_deterministic_and_validated` | APROBADO |
| MEM-01 | Acceso y layout tipados | Copiar entero, booleano, doble y referencia preserva su valor; padding no altera vecinos. | Desalineación, offset fuera de reserva o solapamiento rechazados; no `ld` de referencia de 32 bits. | `test_target_memory.py::test_mem_01_typed_storage` | APROBADO |
| REG-01 | `getReg` conserva valores | `(2 + 3) * (7 - 1)` produce 30; repetición con operandos fijados conserva ambos. | No expulsa un operando fijado ni asigna el mismo registro a dos valores vivos. | `test_registers.py::test_reg_01_allocation_and_pinning` | APROBADO |
| REG-02 | Derrames y recargas | IR con más valores vivos que registros, y banco reducido a dos, produce la suma esperada. Repetir para dobles. | Víctima modificada se almacena antes de perder su registro; slot no solapa otro vivo. | `test_registers.py::test_reg_02_spill_and_reload` | APROBADO |
| REG-03 | Préstamos y respaldo | Nombre `t0` reciclado con leases distintos funciona; muchos tipos reciclados no exceden su plan físico. | Uso de lease liberado o de otro procedimiento se rechaza; no indexar slots por número textual `tN`. | `test_registers.py::test_reg_03_temporary_leases` | APROBADO |
| NUM-01 | Operaciones tipadas | Operadores, comparaciones y `CAST` enteros/dobles; división entera negativa, módulo, límites y normalización booleana. | Literales fuera de rango y tipos IR incompatibles rechazados; cero invoca interfaz de error, nunca resultado inventado. | `test_scalar.py::test_num_01_operations_and_errors` | APROBADO |
| FLOW-01 | Bloques y barreras | Rama tomada/no tomada y bucle con valor modificado producen la salida prevista. | Al llegar a label no se reutiliza un descriptor de otra rama; validar con pocos registros. | `test_scalar.py::test_flow_01_joins_and_loops` | APROBADO |
| SIM-01 | MARS reproducible | Ensamblar y ejecutar IR pequeña, imprimir 30 y terminar en 0; capturar por separado mensajes de MARS. | Casos distintos de JAR ausente, sintaxis ASM inválida, trap MARS, bucle sin término y límite de pasos. | `test_simulator.py::test_sim_01_execution_outcomes` | APROBADO |

## Evidencia y comando de puerta

Además de casos internos, CORE-01, MEM-01, REG-02, NUM-01 y FLOW-01 deben
tener ejecuciones reales en MARS. Los mocks solo prueban errores de herramientas,
no demuestran traducción o asignación correctas.

Comando de puerta implementado:

```powershell
$env:MARS_JAR = 'C:\ruta\Mars4_5.jar'
py -3.14 -m pytest tests/mips --require-mars -q
```

Ejecutar también la regresión completa. `--require-mars` está implementado en
el conftest raíz y exige MARS para que la aceptación no omita integraciones.

## Handoff obligatorio

- Emisor y banco de registros con type hints y contratos de propiedad.
- Protocolo de ubicaciones, llamadas y handlers sin importar módulos futuros.
- Fuente, versión y SHA-256 de MARS; comando y configuración usados.
- Resultados por ID con commit; ninguna fila aprobada por inspección del texto ASM únicamente.
- Registro de la puerta usando [la plantilla](PLANTILLA_ENTREGA_BLOQUE.md).

## Cierre de la puerta

Codigo revisado: `f580a20`; contratos y simulador: `ec7c3fd`.
Suite completa con `--require-mars`: **985 passed**, incluidas **80 pruebas nuevas**, sin skips.
Evidencia por ID, comandos, esperado, resultados y dictamen independiente en
[entrega-bloque1-daniel.md](entrega-bloque1-daniel.md).
La puerta completa se repite con `py -3.14 -m pytest tests --require-mars -q`.

# Arquitectura prevista del backend MIPS

Estado: los componentes de Daniel del bloque 1 están implementados; los de
los bloques 2 a 4 siguen previstos. Sus contratos y reproducción están en
[entrega-bloque1-daniel.md](entrega-bloque1-daniel.md).

## Flujo de datos

```text
Fuente .cps
  → compile_compiscript (existente)
      → ANTLR → semántica → IRProgram verificado + RuntimeLayouts
  → generate_mips
      → validar entrada → planificar bloques, ubicaciones y frames
      → handlers de escalares, llamadas, entornos y runtime
      → verificar referencias y cobertura → ensamblador completo
  → MipsCompilationResult
      → CLI / IDE: mostrar, copiar o exportar
      → ejecución explícita: run_mars → MipsExecutionResult
```

La fase MIPS no recorre de nuevo el árbol sintáctico ni consulta nombres para
resolver símbolos. Consume `IntermediateCodeResult.program`, sus layouts y
los tipos de los operandos. El backend no modifica esos objetos ni la tabla
semántica. El formato TAC previo sigue siendo una vista del IR.

## Interfaces públicas por implementar

```python
generate_mips(intermediate_result: IntermediateCodeResult) -> MipsGenerationResult
compile_to_mips(source: str, source_path: str | Path | None = None) -> MipsCompilationResult
run_mars(assembly: str, config: MarsConfig) -> MipsExecutionResult
```

`compile_to_mips` invoca `compile_compiscript` y solo genera MIPS si este acepta.
No ensambla ni ejecuta automáticamente. `run_mars` usa un archivo temporal,
sin sobrescribir el `.asm` del usuario y sin invocar un shell para construir
comandos. La ejecución es un resultado distinto de la compilación.

### Resultados y configuración

| Tipo propuesto | Campos y reglas |
|---|---|
| `MipsDiagnostic` | `code`, `message`, `location` opcional, `phase`; códigos estables `MIPS-*`. |
| `MipsGenerationResult` | `assembly`, `diagnostics`, `layouts`, `statistics`; `accepted` exige ensamblador completo y cero errores. Rechazo deja `assembly` vacío. |
| `MipsCompilationResult` | `frontend: CompilationResult`, `mips: Optional[MipsGenerationResult]`; `accepted` exige ambos aceptados; `failed_stage` conserva la fase previa o devuelve `mips`. |
| `MarsConfig` | Ruta al JAR, timeout de 10 s, límite de 1 000 000 pasos, delayed branching activado; parámetros positivos y ruta validada. |
| `MipsExecutionResult` | Estado de ensamblado y ejecución, stdout, stderr, código del proceso, diagnóstico de herramienta/runtime, timeout y límite de pasos. |

Los resultados son inmutables. Estadísticas: instrucciones emitidas, frames,
bytes de stack, spills y recargas por procedimiento; no atribuir optimizaciones
o rendimiento no medidos. Una compilación MIPS aceptada no afirma que su
ejecución haya terminado correctamente.

### Contratos entre bloques

Daniel define en `models.py` protocolos consumibles sin importar módulos futuros:

| Contrato | Operaciones mínimas |
|---|---|
| `LocationResolver` | `address_of(symbol, procedure)`, `temporary_slot(lease, procedure)`, `field_offset(owner, abstract_offset)`, `environment_access(owner, depth, offset)`. |
| `CallEmitter` | `emit_call(instruction, pending_parameters, context)`, `emit_return(instruction, context)`. |
| `InstructionHandler` | `supports(opcode)` y `emit(instruction, context)`. Cada opcode tiene un propietario único. |
| `EmissionContext` | Emisor, registros, ubicaciones, unidad actual, mapa fuente, diagnósticos y helpers requeridos. |

El contexto registra todos los destinos antes de emitir cuerpos; un identificador
interno estable se deriva del orden del IR, nunca de `id()` ni de `repr()`.
La identidad de `Symbol` se usa en memoria para consultar tablas, no se escribe
como dirección o etiqueta en el ensamblador.

En bloque 1 se usa un resolver de prueba para IR escalar. Nadissa implementa
el resolver real y el emisor de llamadas. Dulce compone el registro completo
de handlers; no exige modificar el núcleo para importar paquetes futuros.

## Responsabilidades de los módulos previstos

```text
src/mips/
  models.py, diagnostics.py       contratos y resultados — Daniel
  emitter.py, registers.py        emisión, bloques y getReg — Daniel
  scalar.py, runtime_base.py      escalares y helpers básicos — Daniel
  simulator.py                   ensamblar y ejecutar MARS — Daniel
  layout.py, calls.py             direcciones físicas y ABI — Nadissa
  environments.py                entornos y closures — Nadissa
  runtime.py, lists.py, objects.py cadenas y memoria compuesta — Dulce
  exceptions.py                  manejadores y errores runtime — Dulce
  generator.py, pipeline.py       composición y API integral — Dulce
src/gui/mips_results.py           presentación Qt — Nelson
```

`__init__.py` será mínimo. El backend y el adaptador MARS no dependen de Qt.
Los módulos de runtime emiten ensamblador requerido una sola vez por unidad;
no se ejecutan durante la importación de Python.

## Validación y diagnósticos

1. Rechazar una entrada sin programa, layouts o aceptación TAC.
2. Repetir `IRVerifier` al recibir IR por API para detectar clientes malformados.
3. Validar que cada operando tenga representación de máquina resoluble y espacio suficiente.
4. Comprobar handlers, firmas, destinos y auxiliares externos conocidos.
5. Emitir y comprobar etiquetas/reservas; publicar solo el programa completo.
6. Ensamblar y ejecutar mediante MARS cuando lo solicite el consumidor o la prueba.

Errores previstos: `MIPS-INVALID-IR`, `MIPS-MISSING-LAYOUT`,
`MIPS-UNSUPPORTED-OPCODE`, `MIPS-UNKNOWN-EXTERNAL`, `MIPS-UNRESOLVED-TYPE`,
`MIPS-INTEGER-LITERAL-RANGE`, `MIPS-INVALID-ADDRESS`, `MIPS-TOOL-MISSING`,
`MIPS-ASSEMBLY-ERROR`, `MIPS-SIMULATION-ERROR`, `MIPS-TIMEOUT` y
`MIPS-STEP-LIMIT`. Son nombres de diseño; su implementación pertenece al
propietario de cada comportamiento.

Los tipos internos `UNKNOWN` usados como punteros de entorno se resuelven
mediante su rol/layout, no se rechazan indiscriminadamente. Un dato sin tipo
ni rol resoluble sí produce diagnóstico. Los errores inesperados de programación
se reportan como fallo interno en los consumidores, sin convertirlos en ACCEPT.

## IDE y CLI

La CLI conservará `--emit-tac`, `--show-layout` y `--syntax-only`.
Agregará `--emit-mips [RUTA]`, `--run-mips` y `--show-mips-layout`.
`--syntax-only` es incompatible con las opciones MIPS. `--emit-tac` y
`--emit-mips` sin ruta no se pueden combinar porque ambos reclaman stdout.
`--run-mips` se rechaza si cualquiera de `--emit-tac` o `--emit-mips` reclama
stdout por no tener ruta, también al combinar las tres opciones.
Las variantes con rutas explícitas sí pueden combinarse con ejecución.

stdout contiene solo ensamblador al exportarlo por terminal; los diagnósticos
van a stderr. La exportación rechazada conserva cualquier archivo existente.
Los códigos de salida son 0 para éxito, 1 para rechazo o error del programa y
2 para configuración, herramientas, timeout/límite o E/S. Una ejecución agotada
no se presenta como salida correcta del programa.

El IDE añade vista MIPS, layouts físicos diferenciados de los abstractos y
salida MARS. Compilar y ejecutar usan workers; Ejecutar es una acción explícita
habilitada solo sobre la revisión vigente compilada. Editar, abrir o crear
documento invalida esos resultados. Cancelar ejecución termina el proceso Java;
cerrar con worker activo solicita terminarlo y espera su cierre antes de
destruir el objeto Qt. Ninguna señal tardía revive resultados obsoletos.

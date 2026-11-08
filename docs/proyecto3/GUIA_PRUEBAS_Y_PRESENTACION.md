# Guía de pruebas y presentación de MIPS

## Estado de los comandos

Los cuatro bloques están implementados: backend, fixtures `.cps` MIPS con oráculos,
CLI (`--emit-mips`, `--show-mips-layout`, `--run-mips`) e IDE (pestañas MIPS, Frames
MIPS y Ejecución MARS). Los programas de la demostración propuesta existen en
`tests/cps/mips/` con sus oráculos. Comandos y ensayo registrados en
[la entrega del bloque 4](entrega-bloque4-nelson.md).

## Preparación del entorno de aceptación

1. Usar un checkout limpio del commit a evaluar y registrar `git rev-parse HEAD`.
2. Instalar las dependencias Python declaradas y Java; comprobar versiones.
3. Obtener MARS 4.5 de la [distribución oficial](https://dpetersanderson.github.io/), registrar SHA-256 y definir `MARS_JAR`.
4. Comprobar ensamblado/ejecución de un programa mínimo y configuración de branching.
5. Registrar los resultados por ID y guardar logs en `output/qa/proyecto3/`.

El JAR y las caches no son sustitutos de instrucciones de instalación. Se
proporcionará ruta mediante entorno o configuración de la aplicación; no se
dependen de rutas absolutas personales en código versionado.

Comandos directos de referencia, basados en las
[opciones oficiales](https://dpetersanderson.github.io/Help/MarsHelpCommand.html):

```powershell
$env:MARS_JAR = 'C:\ruta\Mars4_5.jar'
Get-FileHash -LiteralPath $env:MARS_JAR -Algorithm SHA256
java -Dfile.encoding=UTF-8 -jar "$env:MARS_JAR" nc me a ae2 programa.asm
java -Dfile.encoding=UTF-8 -jar "$env:MARS_JAR" nc me sm db ae2 se3 1000000 programa.asm
```

El adaptador separa ensamblado y simulación; usa timeout de 10 segundos y límite
de un millón de pasos. El límite de pasos puede dejar código de proceso cero:
examinar además el diagnóstico de terminación de MARS y no aceptar una ejecución
incompleta. `ae2` y `se3` distinguen fallos del ensamblador/simulador de la salida
1 que emite un error controlado del lenguaje. `me` separa mensajes de herramienta
de stdout, pero el diagnóstico runtime del programa sigue perteneciendo a su salida.

## Organización de pruebas

```text
tests/mips/                         unitarias, IR manual y ejecución por API
tests/gui/test_mips_workflow.py     consumidores Qt
tests/test_main_mips_cli.py         consumidor CLI
tests/cps/mips/
  validos/                         programas con ejecución exitosa
  invalidos/                       rechazo de compilación por fase
  runtime/                         errores controlados y catches
  esperados/                       oráculos de salida y estado
```

Cada `.cps` tendrá cabecera `// IDs: ...` y `// Esperado: ACCEPT`,
`// Esperado: REJECT <fase> <codigo>` o `// Esperado: RUNTIME <codigo>`.
Cada fixture tendrá un JSON de igual basename en `esperados/`, con `compile`
(`accepted`, `stage`, `code`) y `execution` (nulo si rechaza; si ejecuta:
`exit_code`, `stdout`, `runtime_code`). Los casos de dobles pueden agregar
`numeric_lines` con número de línea y valor esperado para aplicar la tolerancia
del diseño; el resto de stdout se compara exactamente con LF.

El inventario comprueba correspondencia uno a uno y rechaza basenames
duplicados. Los fixtures no generan su propio oracle con el backend bajo prueba.
Para casos internos imposibles en fuente se usa IR manual y se declara el ID.
No toda fila requiere un `.cps` negativo, pero toda fila requiere comprobación
negativa o de invariante.

## Casos mínimos de comportamiento

| Dominio | Ejemplo y esperado | Caso que debe revelar un defecto |
|---|---|---|
| Aritmética | `(2+3)*(7-1)` → 30; dobles 1.25 + 2.5 → 3.75 | Presión de registros y división por cero. |
| Lógica y ternario | Rama no elegida no modifica contador | RHS con efectos que no debe ejecutarse. |
| Control | if/else, while, do, las formas de for, foreach y switch | continue en for va a actualización; discriminante de switch una sola vez. |
| Llamadas | Sumar seis argumentos → 21; factorial 5 → 120 | Spills vivos antes de llamada y canarios de stack. |
| Closures | Contador escapado → 1, 2; segundo creador → 1 | Hermanas comparten estado; creadores distintos no. |
| Cadenas | Concatenar `Compi` y `script`; texto con acentos | Igualdad por contenido con asignaciones distintas y bytes Unicode. |
| Listas | Suma de `[1,2,3]` → 6; matriz y lista de dobles | Índice -1/longitud y alias que observa una escritura. |
| Objetos | Dos instancias con valores distintos; herencia local | Clase homónima, inicializador base y método ligado escapado. |
| Excepciones | Error en función se captura en caller | Catch que falla llega al exterior; return/break/continue retiran handlers. |
| Rechazos | Caso por fase anterior, IR inválida y externo desconocido | No conservar ensamblador anterior como si fuera del caso actual. |
| Herramientas | Programa termina dentro de límites | JAR ausente, ASM inválido, timeout y pasos agotados diferenciados. |
| IDE | Válido → inválido → válido con edición sin guardar | Exportación obsoleta, cancelación y cierre durante ejecución. |

## Comandos objetivo de aceptación

```powershell
py -3.14 -m pytest tests/mips --require-mars -q
py -3.14 -m pytest tests/gui/test_mips_workflow.py tests/test_main_mips_cli.py --require-mars -q
py -3.14 -m pytest tests -q
git diff --check
```

Daniel implementará `--require-mars` en el conftest raíz. Ese modo falla si
falta el simulador y no omite integraciones. En desarrollo sin MARS se permite
ejecutar unitarias aisladas, pero su resultado no cierra una puerta.

No usar solo conteo de pruebas, golden ASM o mocks como evidencia del backend.
Los logs registran comandos, versión, hash, commit, salida y estado. Una suite
modificada después de aprobarse exige repetir la puerta afectada.

## Demostración propuesta

Nelson preparará los fixtures siguientes y sus oráculos:

1. `DEMO-completa.cps`: abrir en IDE, compilar buffer actual, mostrar TAC,
   ASM, frame físico y salida correcta. Exportar y ejecutar el `.asm` en MARS.
2. `REG-presion.cps`: mostrar derrames, recargas y salida esperada; explicar `getReg`.
3. `CALL-recursion.cps`: factorial y más de cuatro parámetros; enseñar `$sp`,
   `$fp`, `$ra`, argumentos y retorno antes/después.
4. `ENV-escape.cps`: closure después del creador y estado compartido entre hermanas.
5. `OBJ-herencia-local.cps`: objeto, clase base con entorno distinto y método ligado.
6. `EXC-captura.cps`: error desde función anidada, catch y continuación correcta.
7. `ERROR-tipos.cps`: rechazo semántico sin ASM; volver al válido y verificar
   que solo se exportan resultados actuales.
8. Repetir por CLI con `--emit-mips salida.asm`, `--show-mips-layout` y
   `--run-mips`. Cancelar una ejecución larga sin bloquear Qt.

La defensa de Daniel explica emisión y registros; Nadissa explica llamadas y
entornos; Dulce explica traducción completa/runtime; Nelson explica IDE, CLI y
evidencia. Cada uno debe poder ejecutar las pruebas de su matriz y justificar
una negativa. Registrar el ensayo visible y distinguirlo de automatización Qt.

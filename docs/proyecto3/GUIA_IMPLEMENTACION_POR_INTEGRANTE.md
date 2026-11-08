# Guía de implementación por integrante para MIPS

## Contratos antes de programar

Los bloques 1, 2 y 3 ya están implementados; ver [su entrega](entrega-bloque1-daniel.md),
[la del bloque 2](entrega-bloque2-nadissa.md) y [la del bloque 3](entrega-bloque3-dulce.md).
El bloque 4 sigue siendo trabajo futuro. Leer primero [PLAN.md](PLAN.md),
[ARQUITECTURA.md](ARQUITECTURA.md), [DISENO_MIPS.md](DISENO_MIPS.md) y la
matriz propia. El IR y layouts existentes están en `src/codegen/`; el backend
nuevo se alojará en `src/mips/`. No modificar la gramática para traducir TAC.

El desarrollo de cada comportamiento sigue: prueba que demuestra el fallo,
implementación, ejecución del caso, regresión, documentación y revisión de puerta.
Las pruebas de backend deben poder inyectar IR manual inválida sin pasar por el
parser. Los casos `.cps` verifican además toda la integración.

## Daniel Chet

### Módulos y contratos

Implementar `models.py`, `diagnostics.py`, `emitter.py`, `registers.py`,
`scalar.py`, `runtime_base.py` y `simulator.py`. Dejar `__init__.py` pequeño.
Definir todos los contratos de arquitectura, incluidos los que implementarán
los siguientes bloques, mediante protocolos y tipos sin importar esos módulos.

El emisor administra secciones, labels globales/locales mangled, constantes,
helpers requeridos y mapa instrucción fuente → ensamblador. Escapar/manglear
etiquetas de procedimientos con puntos o nombres coincidentes con `main`,
registros o helpers. La emisión es determinista y valida destinos.

El planificador identifica bloques básicos por labels, jumps, returns y
entradas de catch; los descriptores de registros nunca cruzan una frontera
sin respaldo. El plan de vidas debe considerar ramas y ciclos; se puede
sobrerreservar slots conservadoramente antes que reutilizar uno aún vivo.

Exponer `flush`, `invalidate`, `pin`, `unpin` y `release`, además de `getReg`.
Pruebas pueden reducir la cantidad de registros disponibles sin alterar las
reservas de scratch. Implementar también operaciones de doble y su banco propio.

Los helpers base son reserva alineada, impresión escalar y terminación de error.
Las operaciones escalares llaman una interfaz de error y una interfaz de
operación de cadena; los handlers finales se inyectan al componer el backend.
No incluir saltos a etiquetas inexistentes como supuesto de integración.

### Simulador y pruebas

Crear configuración `MARS_JAR` y registro de versión/hash. Una ruta inexistente
produce diagnóstico; importar el paquete no descarga ni ejecuta herramientas.
Adaptador con `subprocess` y lista de argumentos, timeout y cierre del proceso.
Crear `--require-mars` en `tests/conftest.py` y fixtures de IR/MARS en
`tests/mips/conftest.py`, sin importar Qt ni el pipeline aún inexistente.

Realizar primero unitarias del emisor/registros; después integración con MARS.
La matriz propia especifica los archivos y escenarios. Dejar documentación de
cómo ejecutar esas pruebas antes de crear la rama de Nadissa.

## Nadissa Vela

### Layouts y llamadas

Implementar `layout.py`, `calls.py` y `environments.py` sobre los protocolos del
bloque 1. Consultar `SymbolLayoutTable`, `ActivationRecordLayout`,
`EnvironmentLayout` e identidades de `Symbol` sin cambiar sus objetos.
El mapa físico distingue parámetros entrantes, locales, capturas, temporales,
header y spills; conserva las regiones de objetos/entornos con padding.

Planificar todos los procedimientos antes de emitirlos. El descriptor conoce
tamaño de frame y firma completa, incluidos ocultos, y el layout de entornos
de cada ancestro. Un nombre de clase o de variable no es clave suficiente.

Implementar prólogo/epílogo según la fórmula del diseño. Antes de `jal`, `jalr`
o un helper, materializar valores vivos y construir el paquete físico.
Las llamadas indirectas agregan ocultos desde el callable descriptor; las
directas no duplican los `PARAM` ocultos que ya incluye el TAC.

### Entornos y métodos ligados

Reservar entornos de capturas en heap mediante el auxiliar de Daniel.
`ENV_GET` con profundidad recorre parent links por sus layouts correspondientes;
`ENV_SET` modifica la celda compartida. Cerrar sobre una variable no copia su
estado a un entorno independiente por hermana.

`CLOSURE` y `METHOD_REF` crean descriptors de código/entorno/receptor/máscara.
La llamada indirecta consulta la máscara en runtime: un `FunctionType` puede
contener distintas clases de callable sin cambiar su firma fuente.
Para método ligado, obtener el entorno del objeto mediante el offset que trae
el procedimiento. La prueba usa un receptor preparado en memoria, sin exigir
el handler `OBJECT_NEW` del siguiente bloque.

Ejecutar casos de recursión, retorno mixto, capturas y canarios en MARS.
La puerta no acepta únicamente inspección de prólogos en texto.

## Dulce Ambrosio

### Runtime y composición

Implementar `runtime.py`, `lists.py`, `objects.py`, `exceptions.py`,
`generator.py` y `pipeline.py`. Componer handlers escalares, llamadas, entornos
y memoria compuesta. Cada opcode tiene handler o diagnóstico explícito.
La cobertura comprueba el enum real, no una lista copiada dentro del test.

Extender la impresión base con cadenas y marcadores de valores compuestos.
Para suma y comparación de cadenas, despachar según tipo; conservar aritmética
y comparación numéricas del bloque 1. Añadir tests Unicode y de llamadas a
helpers con otros valores vivos para detectar clobbering.

Listas usan length y stride 8; campos usan el descriptor de clase y offsets
del IR. El TAC ya emite constructores e inicializadores: no volver a ejecutarlos
automáticamente en `OBJECT_NEW` y duplicar sus efectos. Respetar inicializadores
heredados y entornos base/derivada que ya codifica el Proyecto 2.

Excepciones instalan y retiran registros de manejador en stack. Conectar el
proveedor de error de Daniel a `raise_runtime` sin reescribir operaciones
numéricas. Las pruebas entre frames son obligatorias; un catch local no
demuestra desenrollado. Respetar los `TRY_END` que emite el lowering actual.

### Pipeline y fixtures

`generate_mips` recibe el resultado TAC aceptado; `compile_to_mips` coordina
el frontend existente y devuelve su resultado íntegro junto con MIPS. Mantener
`CompilationResult.accepted` y las opciones previas sin cambios de significado.
Los errores de backend dejan ensamblador vacío y diagnósticos con ubicación.

Crear fixtures `.cps` y oráculos por dominio con el contrato de
[GUIA_PRUEBAS_Y_PRESENTACION.md](GUIA_PRUEBAS_Y_PRESENTACION.md). Reutilizar
programas del Proyecto 2 como regresión, sin modificar su resultado esperado
TAC para facilitar el backend.

## Nelson Escalante

### Consumidores

Extender `src/main.py` con las opciones y códigos de arquitectura; crear
pruebas CLI con archivos temporales y captura de stdout/stderr.
Exportación UTF-8/LF, sin mezclar reportes ni ejecución con stdout reservado
al ASM. Conservar un archivo existente cuando la compilación sea rechazada.

Agregar `src/gui/mips_results.py` y conectar `src/gui/app.py` al pipeline.
Pestañas de MIPS, layouts físicos y ejecución; nombres que permitan distinguir
el frame abstracto previo de su ubicación real. El worker entrega la revisión
de documento que inició la operación. Cambiar identidad o texto invalida las
operaciones posteriores y descarta respuestas viejas.

Implementar cancelación y cierre del proceso MARS, seguido del cierre seguro
del worker. No confiar en un timeout para dejar congelada la ventana ni en
destruir `QThread` mientras está activo. Mantener los avisos de guardado existentes.

### Aceptación y documentación

Crear inventario parametrizado de fixtures, comprobar oráculos presentes y
ejecutar tanto API como consumidores. Las pruebas de Qt pueden simular acciones
humanas, pero las de generación/ejecución deben usar MARS real.
Actualizar el README solo con comandos implementados y comprobados.

Preparar un checkout limpio con dependencias declaradas; repetir la demo en
Windows visible y registrar quién la repitió. Consolidar evidencias por ID y
autoría. Documentar incidencias sin ocultarlas mediante skips o cambio de alcance.

## Registro de aceptación de cada bloque

Usar [PLANTILLA_ENTREGA_BLOQUE.md](PLANTILLA_ENTREGA_BLOQUE.md) para crear
`entrega-bloque1-daniel.md`, `entrega-bloque2-nadissa.md`,
`entrega-bloque3-dulce.md` y `entrega-bloque4-nelson.md` al cerrar cada trabajo.
Estos archivos se crean con evidencia real; no se incluyen ahora como entregas
aparentemente realizadas. Un revisor registra dictamen y pruebas repetidas.

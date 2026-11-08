# Compiscript — compilador hasta MIPS32 (MARS 4.5)

Proyecto de Construcción de Compiladores para programas Compiscript (`.cps`).
La gramática combinada de ANTLR produce el lexer, el parser y el árbol
sintáctico; el análisis semántico valida tipos, ámbitos, funciones, control de
flujo, clases y arreglos; y el **Proyecto 2** agrega la generación de **código
de tres direcciones (TAC)** con reciclaje de temporales, una tabla de símbolos
extendida (direcciones, offsets, tamaños, etiquetas) y registros de activación.
La **fase 3** traduce ese TAC a **ensamblador MIPS32** que se ejecuta en
**MARS 4.5**, desde el IDE o la terminal.

La entrega semántica calificada con **100/100** permanece disponible en la
etiqueta Git `entrega-semantica-100`.

## Flujo

```text
programa.cps
    ↓
Compiscript.g4 → Lexer y Parser de ANTLR → árbol sintáctico común
    ↓ solo si no hay errores léxicos ni sintácticos
compiscript.semantic.json → análisis semántico + tabla de símbolos
    ↓ solo si no hay errores semánticos (los warnings no bloquean)
anotaciones por nodo + layouts de símbolos y registros de activación
    ↓
generador TAC (cuádruplos) → IRVerifier
    ↓ solo si la IR verifica
TAC textual + tabla extendida + frames + estadísticas de temporales
    ↓ solo si el TAC es aceptado
generate_mips → ensamblador MIPS32 + frames físicos + estadísticas
    ↓ acción explícita
MARS 4.5 → salida del programa y estado de la ejecución
    ↓
IDE o CLI (mismas APIs públicas: compile_compiscript / generate_mips)
```

Una entrada inválida nunca produce TAC: la compilación se detiene en la primera
fase que falla y reporta sus diagnósticos con tipo y ubicación.

## Estructura

```text
src/
├── antlr_mode/                      # Generación, caché y ejecución de ANTLR
├── compiscript/grammar/
│   └── Compiscript.g4               # Gramática oficial
├── semantic/                        # Tipos, símbolos, acciones y anotaciones
├── codegen/                         # Proyecto 2: IR, layouts, lowering y pipeline
│   ├── ir.py, builder.py, names.py  # Cuádruplos, emisión, temporales y etiquetas
│   ├── verifier.py, formatter.py    # Verificador de IR y TAC textual
│   ├── layout.py, activation.py     # Tabla extendida y registros de activación
│   ├── generator.py, statements.py, control_flow.py, callables.py, objects.py
│   ├── results.py                   # IntermediateCodeResult / CompilationResult
│   └── pipeline.py                  # compile_compiscript (API única)
├── mips/                            # Fase 3: backend MIPS32, runtime y adaptador MARS
├── mips_consumer.py                 # Utilidades sin Qt de CLI/IDE: exportación segura,
│                                    #   frames físicos y ejecución MARS cancelable
├── gui/
│   ├── app.py                       # IDE: editor, workers y pestañas
│   ├── codegen_results.py           # Vistas de TAC, tabla extendida y diagnósticos
│   ├── mips_results.py              # Vistas de MIPS, frames físicos y ejecución
│   ├── semantic_results.py          # Diagnósticos y tabla de símbolos por ámbito
│   └── parse_tree_view.py           # Árbol navegable
└── main.py                          # GUI y CLI

semantic_profiles/compiscript.semantic.json
docs/proyecto2/                      # Diseño TAC, arquitectura, matriz y entregas
docs/proyecto3/                      # Diseño MIPS, matrices, entregas y guía de defensa
tests/
├── antlr_mode/  codegen/  gui/  mips/  semantic/
├── cps/                             # Programas de la fase semántica
├── cps/codegen/                     # Programas y TAC esperado del Proyecto 2
├── cps/mips/                        # Programas MIPS y oráculos JSON de ejecución
├── test_main_cli.py
└── test_main_mips_cli.py
```

## Requisitos e instalación

- Python 3.10 o superior (probado con 3.14).
- Java 11 o superior para generar el parser de ANTLR.
- Graphviz en `PATH` (opcional; solo para la imagen del árbol en el IDE).
- MARS 4.5 (`Mars4_5.jar`) para ejecutar MIPS; la aplicación nunca lo descarga.

```powershell
git clone --branch feature/proyecto2-codegen https://github.com/EscasanN/Generador_Sintactico_Compis2.git
cd Generador_Sintactico_Compis2
python -m pip install -r requirements.txt
```

En la primera ejecución el frontend descarga ANTLR 4.13.2 y guarda el JAR y los
archivos generados en `output/antlr/` (ignorado por Git). También puede
definirse `ANTLR4_JAR` con una ruta local al JAR.

### MARS 4.5

Descargue el JAR oficial (enlazado desde
[dpetersanderson.github.io](https://dpetersanderson.github.io/)), compruebe su
hash y guárdelo en `output/mips/tools/Mars4_5.jar` (ignorado por Git) o indique
su ruta con `MARS_JAR`:

```powershell
New-Item -ItemType Directory -Force output/mips/tools | Out-Null
Invoke-WebRequest https://raw.githubusercontent.com/dpetersanderson/dpetersanderson.github.io/master/Mars4_5.jar -OutFile output/mips/tools/Mars4_5.jar
(Get-FileHash output/mips/tools/Mars4_5.jar -Algorithm SHA256).Hash
# Debe ser AC340B676BA2B62246B9DF77E62F81AD4447BCFD329AB539716BCD09950B7096 (4 169 142 bytes)
$env:MARS_JAR = (Resolve-Path output/mips/tools/Mars4_5.jar).Path
```

Sin `MARS_JAR` el IDE y la CLI usan `output/mips/tools/Mars4_5.jar` del checkout.

## Uso

### IDE

```powershell
python -m src.main
```

1. **Nuevo / Abrir .cps** o escribir directamente en el editor.
   Si hay cambios pendientes, abrir, crear o cerrar ofrece guardar, descartar o
   cancelar. Un guardado fallido o cancelado conserva el programa. Pulsar su fila
   en **Programa** no recarga el archivo ni pierde el historial de deshacer.
2. **Compilar** (botón, `Ctrl+R` o `F5`). Compila el contenido actual del
   editor, aunque no esté guardado, en un hilo separado; el botón se deshabilita
   mientras compila y los resultados anteriores se limpian al empezar.
   Editar o cambiar de documento invalida los resultados; una respuesta atrasada
   del worker no se muestra como si perteneciera al documento actual.
3. Pestañas de resultado:
   - **Árbol**: imagen Graphviz y árbol navegable.
   - **Semántica**: diagnósticos semánticos y tabla de símbolos por ámbito.
   - **Código TAC**: TAC verificado en fuente monoespaciada, con búsqueda,
     copia y **Exportar .tac…** (`Ctrl+E`).
   - **Tabla extendida**: almacenamiento, offset, tamaño, alineación, etiqueta,
     nivel léxico y frame de cada símbolo; debajo, cada registro de activación
     con encabezado (dirección y valor de retorno, enlace de control y de
     acceso), parámetros ocultos y declarados, locales, temporales, capturas,
     entorno de closure y tamaño total.
   - **MIPS**: ensamblador MIPS32 completo con búsqueda, copia y
     **Exportar .asm…** (`Ctrl+Shift+E`); estadísticas de instrucciones,
     frames, bytes de pila, derrames y recargas.
   - **Frames MIPS**: área estática `$gp` y cada frame físico MIPS32 con
     encabezado (`$ra`, `$fp` anterior, enlace de acceso, valor de retorno),
     argumentos entrantes, locales, celdas de temporales reutilizadas y
     argumentos salientes; se distingue del registro abstracto del TAC.
   - **Ejecución MARS**: **Ejecutar en MARS** (`F6`) y **Cancelar** (`Ctrl+.`),
     salida del programa, estado (`success`, `runtime_error`, `timeout`,
     `step_limit`, `tool_error`, `cancelled`…) y mensajes de MARS.
   - **Resumen**: estado por fase y tabla única de diagnósticos léxicos,
     sintácticos, semánticos y de generación con fase, tipo, línea y columna.

Ejecutar se habilita solo para el MIPS de la revisión vigente del documento.
Editar, abrir o crear un documento invalida ASM, frames y ejecución; si MARS
estaba corriendo se termina y su salida no se muestra. Cancelar o cerrar la
ventana durante una ejecución termina el proceso Java y espera a los workers.
La exportación escribe un archivo temporal y lo reemplaza: un rechazo, una
cancelación o un error de E/S nunca destruye un `.asm` existente.

Cambiar tema conserva la pestaña y navegación actuales. Si **Nuevo** selecciona
el archivo que acaba de guardar el aviso de cambios, se conserva ese contenido
y se pide elegir otro nombre; no se vacía el archivo recién guardado.

### Terminal

```powershell
# Compila y muestra diagnósticos, tabla de símbolos y estadísticas del TAC
python -m src.main --cps tests/cps/codegen/validos/DEMO-completa.cps

# Imprime solo el TAC en stdout (diagnósticos y estado van a stderr)
python -m src.main --cps tests/cps/codegen/validos/DEMO-completa.cps --emit-tac

# Guarda el TAC en un archivo UTF-8 (LF)
python -m src.main --cps tests/cps/codegen/validos/DEMO-completa.cps --emit-tac salida.tac

# Agrega la tabla de símbolos extendida y los registros de activación
python -m src.main --cps tests/cps/codegen/validos/FUN-07-closures.cps --show-layout

# Solo lexer y parser
python -m src.main --cps tests/cps/demostracion-valida.cps --syntax-only

# MIPS: imprime solo el ensamblador en stdout (diagnósticos en stderr)
python -m src.main --cps tests/cps/mips/validos/DEMO-completa.cps --emit-mips

# MIPS: guarda el .asm, muestra frames físicos y ejecuta en MARS
python -m src.main --cps tests/cps/mips/validos/DEMO-completa.cps --emit-mips salida.asm --show-mips-layout --run-mips
```

`--syntax-only` no se combina con opciones de TAC o MIPS; `--emit-tac` y
`--emit-mips` sin ruta no se combinan (ambos reclaman stdout), y `--run-mips`
exige que toda exportación indique una ruta. Con `--run-mips` la salida del
programa aparece entre `----- salida del programa (MARS) -----` y
`----- fin de la salida -----`, seguida de la línea `EJECUCIÓN: …`.

Códigos de salida:

| Código | Significado |
|---:|---|
| `0` | Compilación aceptada (TAC, y MIPS si se pidió) y, con `--run-mips`, ejecución correcta. |
| `1` | Rechazo léxico, sintáctico, semántico, de TAC o MIPS, o error del programa al ejecutarse (`RuntimeError: …`). |
| `2` | Lectura/escritura, opciones incompatibles, Java/MARS ausente, ensamblado rechazado, tiempo (10 s) o límite de pasos (1 000 000) agotado. |

El IDE y la CLI muestran exactamente el mismo TAC porque ambos usan
`compile_compiscript` y el mismo formato (`tac_document`).

Si una exportación se rechaza, un `.tac` existente no se sobrescribe ni elimina:
la CLI indica que no fue actualizado. Las funciones no `void` con una salida
alcanzable sin valor se rechazan con `IRGEN-MISSING-RETURN`.

## Pruebas

```powershell
python -m pytest tests -q                    # suite completa
python -m pytest tests/codegen -q            # IR, layouts, lowering, pipeline y fixtures
python -m pytest tests/semantic -q           # regresión de la fase semántica
python -m pytest tests/antlr_mode -q
python -m pytest tests/gui -q                # IDE (Qt en modo offscreen)
python -m pytest tests/test_main_cli.py -q   # CLI
```

Fase 3, con MARS obligatorio (falla si el simulador no está configurado):

```powershell
py -3.14 -m pytest tests/gui/test_mips_workflow.py tests/test_main_mips_cli.py tests/mips --require-mars -q
py -3.14 -m pytest tests --require-mars -q
```

`tests/cps/mips` contiene cada programa con un oráculo JSON escrito a mano
(salida exacta, código de proceso y error runtime esperado);
`tests/mips/test_mips_fixtures.py` los descubre y comprueba que API, CLI e IDE
producen el mismo ensamblador y la salida esperada en MARS.

La batería de casos `.cps` del Proyecto 2 está en
[tests/cps/codegen](tests/cps/codegen/README.md): un programa válido por dominio
de la matriz, programas inválidos por fase y TAC esperado (golden) para casos
representativos.

## Demostración

Fase 3 (MIPS): guía y programas en
[docs/proyecto3/entrega-bloque4-nelson.md](docs/proyecto3/entrega-bloque4-nelson.md#ensayo-de-la-demostración)
y `tests/cps/mips/` (`DEMO-completa`, `REG-presion`, `CALL-recursion`,
`ENV-escape`, `OBJ-herencia-local`, `EXC-captura`, `ERROR-tipos`).

Proyecto 2 (TAC): ver la guía en
[docs/proyecto2/bloque4-entrega.md](docs/proyecto2/bloque4-entrega.md#guía-de-demostración).
Programas preparados:

- válido completo: `tests/cps/codegen/validos/DEMO-completa.cps`;
- fallido: `tests/cps/codegen/invalidos/DEMO-fallida.cps`.
- regresiones del cierre y guía ampliada:
  [AUDITORIA_FINAL.md](docs/proyecto2/AUDITORIA_FINAL.md).

## Backend MIPS de la fase 3

Daniel implementó emisión, registros y el adaptador MARS; Nadissa, frames,
llamadas y closures; Dulce, el runtime completo y `compile_to_mips`; Nelson,
el IDE, la CLI, los fixtures integrales y la entrega. Las entregas por bloque
están en [docs/proyecto3](docs/proyecto3/README.md). El ejemplo de IR manual del
bloque 1 sigue disponible:

```powershell
py -3.14 -m scripts.demo_mips_core --output output/mips/demo.asm
```

## Documentación

- [docs/proyecto3/README.md](docs/proyecto3/README.md): planificación de la
  fase 3 MIPS para MARS, división en cuatro bloques y matrices por integrante.
  **Estado: bloque 1 aprobado; bloques 2, 3 y 4 implementados con revisión
  pendiente.** Ver las entregas de
  [Daniel](docs/proyecto3/entrega-bloque1-daniel.md),
  [Nadissa](docs/proyecto3/entrega-bloque2-nadissa.md),
  [Dulce](docs/proyecto3/entrega-bloque3-dulce.md) y
  [Nelson](docs/proyecto3/entrega-bloque4-nelson.md).
- [docs/proyecto2/DISENO_TAC.md](docs/proyecto2/DISENO_TAC.md): lenguaje
  intermedio, instrucciones, supuestos y ejemplos de traducción.
- [docs/proyecto2/ARQUITECTURA.md](docs/proyecto2/ARQUITECTURA.md): fases y
  contratos públicos.
- [docs/proyecto2/MATRIZ_CUMPLIMIENTO.md](docs/proyecto2/MATRIZ_CUMPLIMIENTO.md):
  requisitos con su evidencia.
- Entregas por bloque: [bloque 2](docs/proyecto2/bloque2-entrega.md),
  [bloque 3](docs/proyecto2/bloque3-entrega.md),
  [bloque 4](docs/proyecto2/bloque4-entrega.md).
- [docs/phase3/README.md](docs/phase3/README.md): análisis semántico.

## Perfil semántico

`semantic_profiles/compiscript.semantic.json` contiene únicamente datos y
nombres de acciones permitidas. Su fingerprint vincula el perfil con la fuente
normalizada de `Compiscript.g4`; si la gramática cambia intencionalmente, el
perfil debe revisarse y actualizarse junto con sus pruebas.

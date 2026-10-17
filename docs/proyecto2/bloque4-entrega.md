# Bloque 4: IDE, CLI, batería de pruebas y entrega

Cierre del Proyecto 2. Presenta el pipeline de Dulce (`compile_compiscript`)
desde el IDE y la CLI, agrega la batería `.cps` con TAC esperado y actualiza la
documentación. No introduce reglas de compilación: la GUI y la CLI solo leen
`CompilationResult`.

## Archivos

| Archivo | Contenido |
|---|---|
| `src/main.py` | CLI `--cps` sobre `compile_compiscript`: `--emit-tac [RUTA]`, `--show-layout`, `--syntax-only`; reporte por fase; `tac_document`. |
| `src/gui/app.py` | Acción **Compilar** (`Ctrl+R`/`F5`), `CompilationWorker` (QThread), limpieza de resultados al iniciar, exportación de TAC y pestañas nuevas. |
| `src/gui/codegen_results.py` | `TacView` (TAC monoespaciado con búsqueda, copia y exportación), `LayoutPanel` (tabla extendida y registros de activación), `DiagnosticsTable` y `collect_diagnostics` (todas las fases). |
| `tests/test_main_cli.py` | OUT-01, OUT-02, rechazos por fase, códigos de salida y `--show-layout`. |
| `tests/gui/test_codegen_results.py` | OUT-03, OUT-04, OUT-05, IDE-01, IDE-02, IDE-03 sobre la ventana real. |
| `tests/gui/test_cps_workflow.py` | Flujo `.cps` existente adaptado a `CompilationWorker` y `_run_compilation`. |
| `tests/codegen/test_codegen_fixtures.py` | Inventario, positivos, negativos por fase, golden TAC y cobertura de IDs (TST-01…03). |
| `tests/cps/codegen/` | 15 programas válidos, 10 inválidos y 7 TAC esperados ([README](../../tests/cps/codegen/README.md)). |
| `README.md`, `tests/README.md` | Instalación, ejecución del IDE y la CLI, pruebas y demostración. |
| `docs/proyecto2/` | Matriz con evidencia por ID, plan, arquitectura (CLI e IDE) y este documento. |

## CLI

```powershell
python -m src.main --cps programa.cps                      # reporte completo
python -m src.main --cps programa.cps --emit-tac           # solo TAC en stdout
python -m src.main --cps programa.cps --emit-tac salida.tac
python -m src.main --cps programa.cps --show-layout        # tabla extendida + frames
python -m src.main --cps programa.cps --syntax-only
```

- Sin `--emit-tac`: diagnósticos de cada fase, tabla de símbolos semántica,
  estadísticas del TAC y la línea `ACCEPT`/`REJECT` (con la fase que falló).
- `--emit-tac` sin ruta: **stdout contiene únicamente el TAC**; diagnósticos y
  estado van a stderr. Así `> salida.tac` produce un archivo limpio.
- `--emit-tac RUTA`: crea las carpetas necesarias y escribe UTF-8 con LF; si la
  compilación se rechaza no se crea el archivo.
- `--show-layout`: columnas Nombre, Clase, Tipo, Almacenamiento, Offset, Tamaño,
  Etiqueta, Nivel, Frame y offset en el entorno; después cada frame con los
  rangos `[offset..fin)` de sus slots, capturas y entorno de closure.
- Códigos: `0` aceptado; `1` rechazo léxico, sintáctico, semántico o IR; `2`
  lectura/escritura, opciones inválidas (`--syntax-only` con opciones de TAC) o
  dependencias (`AntlrModeError`, `GrammarInfoError`, `SemanticAdapterError`).
- En la consola la salida se reconfigura a UTF-8 para no corromper acentos en
  Windows.

## IDE

Pestañas: **Árbol**, **Semántica**, **Código TAC**, **Tabla extendida** y
**Resumen**.

- **Compilar** usa el contenido actual del editor, aunque no esté guardado o no
  exista archivo.
- Al iniciar se limpian árbol, semántica, TAC, tabla, frames y diagnósticos, y
  se deshabilitan el botón y la acción del menú hasta recibir el resultado
  (IDE-02, IDE-03). Un segundo clic mientras compila se ignora.
- `CompilationWorker.run` llama a `compile_compiscript` y renderiza el árbol
  con Graphviz; el hilo de Qt solo recibe el bundle inmutable por la señal
  `completed` (o `failed` para errores de configuración o internos).
- Resultado aceptado: se abre **Código TAC** con el mismo texto que imprime la
  CLI, estadísticas (instrucciones, procedimientos, temporales creados y pico)
  y los botones Buscar, Copiar y Exportar `.tac…` (también `Ctrl+E`).
- Resultado rechazado: se abre **Resumen**; TAC y tabla extendida muestran por
  qué no existen. La tabla de diagnósticos reúne fase (léxica, sintáctica,
  semántica, generación), severidad, tipo (categoría semántica o código
  `IRGEN-*`/`IR-*`), línea, columna y mensaje (OUT-05).
- El editor y el TAC usan fuente monoespaciada también bajo el tema oscuro.

## Batería `.cps`

Cada archivo empieza con `// IDs: …` y `// Esperado: ACCEPT` o
`// Esperado: REJECT <fase> [código]`. `test_codegen_fixtures.py`:

- descubre todos los archivos (agregar uno sin cabecera falla);
- exige TAC verificado, tabla extendida y un frame por procedimiento en cada
  válido;
- exige la fase declarada, diagnósticos y ausencia de TAC en cada inválido;
- comprueba que los válidos cubren todos los IDs de EXP, CTL, FUN, CLS, LST,
  TMP, PIPE-03/05 y EXT-01…07, y que hay rechazos en `syntax`, `semantic` y
  `codegen`;
- compara los golden de `esperados/` y, si cambian, indica el comando para
  regenerarlos;
- verifica estructura por dominio (opcodes especializados, reciclaje con
  `temporary_peak < temporaries_created`, recursión a la propia etiqueta,
  capturas a distancia 1 por enlace de acceso, discriminante del switch
  evaluado una vez).

## Decisiones adoptadas

- **Una sola API.** IDE y CLI llaman a `compile_compiscript`; ninguno importa
  el generador, el builder ni el verificador (hay una prueba que lo revisa en
  `src/gui`).
- **Mismo texto TAC.** `tac_document` (en `src/main.py`, sin Qt) agrega solo el
  salto de línea final; la GUI lo importa para mostrar y exportar.
- **El `.cps` sin guardar también compila.** El IDE ya no exige crear un archivo
  antes de compilar; el resumen lo indica como “editor sin guardar”.
- **Fuentes de verdad de las pruebas.** Los golden se limitan a 7 programas
  representativos; el resto se valida sobre la IR estructurada (regla de la
  guía para no volver frágil la suite).
- **Saltos de línea.** `.gitattributes` fija LF para `.cps` y `.tac`, y la CLI
  y la GUI escriben LF, de modo que un golden es idéntico en Windows y Linux.

## Excepciones a la propiedad de archivos

- `tests/semantic/test_cps_programs.py` (fase semántica): el inventario de
  `tests/cps` excluye ahora la subcarpeta `codegen/`, que tiene su propio
  inventario. No cambió ninguna otra aserción.
- `tests/antlr_mode/test_gui_mode.py` no se modificó; `_render_bundle` sigue
  aceptando el bundle semántico anterior (sin `compilation`).
- No se modificaron `Compiscript.g4`, el perfil semántico ni `src/codegen`.

## Resultado de las pruebas

Ejecutado el 2026-10-17 en Windows 11, Python 3.14.3, Java 26:

```powershell
python -m pytest tests -q              # 790 passed
python -m pytest tests/codegen -q      # 366 passed
python -m pytest tests/semantic -q     # 371 passed
python -m pytest tests/antlr_mode -q   # 12 passed
python -m pytest tests/gui -q          # 26 passed
python -m pytest tests/test_main_cli.py -q   # 15 passed
```

La base heredada del bloque 3 tenía 688 pruebas; ninguna se eliminó.

TST-05: la suite también pasa (790) en una copia que contiene solo los
archivos versionados, sin `output/`; en ese caso el frontend descarga ANTLR y
genera el parser en la primera prueba.

## Guía de demostración

Preparación (una vez): `python -m pip install -r requirements.txt` y
`python -m pytest tests -q`.

1. **Programa válido completo.** `python -m src.main`, abrir
   `tests/cps/codegen/validos/DEMO-completa.cps` y presionar **Compilar**.
   Mostrar en **Código TAC**: global y procedimientos separados, `call
   fn_factorial` dentro de `fn_factorial` (recursión), `closure`/`env_get` en
   `fn_acumulador.sumar`, `object_new` + `call Cuenta.constructor`,
   `list_new`/`list_set`/`list_get`, el `foreach` indexado y el `switch`.
2. **Temporales reciclados.** Abrir `TMP-01-reciclaje.cps`: el estado indica,
   por ejemplo, 3 temporales vivos como pico frente a muchos creados; en el TAC
   `t0`/`t1` se reutilizan después de cada `release`.
3. **Tabla extendida y frames.** Abrir `FUN-07-closures.cps` → **Tabla
   extendida**: `cuenta` con almacenamiento `captured`, etiquetas `fn_*` y el
   frame `fn_contador.incrementar.doble` con encabezado (retorno, enlace de
   control, enlace de acceso, valor de retorno), `env` oculto, temporales y la
   captura “dueño fn_contador, distancia 1”.
4. **Clase con constructor y lista.** `CLS-01-objetos.cps` y
   `LST-01-listas.cps`.
5. **Programa fallido.** Abrir `tests/cps/codegen/invalidos/DEMO-fallida.cps`
   y compilar: la pestaña **Resumen** lista tres errores semánticos (type,
   function, scope) con línea y columna, y **Código TAC** queda vacío con el
   motivo; compilar luego el demo válido y volver al fallido muestra que el TAC
   anterior no se conserva.
6. **Error de generación.** `PIPE-04-error-generacion.cps` muestra
   `IRGEN-UNSUPPORTED-NODE` con su ubicación, sin TAC parcial.
7. **CLI.** El mismo TAC desde la terminal:

   ```powershell
   python -m src.main --cps tests/cps/codegen/validos/DEMO-completa.cps --emit-tac
   python -m src.main --cps tests/cps/codegen/validos/FUN-07-closures.cps --show-layout
   python -m src.main --cps tests/cps/codegen/invalidos/DEMO-fallida.cps
   ```

8. **Batería.** `python -m pytest tests/codegen/test_codegen_fixtures.py -v`.

## Limitaciones conocidas

Heredadas del bloque 3 y visibles como diagnósticos explícitos (nunca TAC
parcial):

- `this` dentro de una función anidada en un método → `IRGEN-THIS-UNAVAILABLE`
  (fixture `PIPE-04-this-en-funcion-anidada.cps`).
- Acceso estático `Clase.campo` → `IRGEN-UNSUPPORTED-NODE`
  (`PIPE-04-error-generacion.cps`).
- Una función sin capturas no puede llamar a una closure hermana que necesita
  entorno → `IRGEN-ENV-UNAVAILABLE`.
- try/catch es IR de alto nivel; métodos por tipo estático, sin vtables.

Del bloque 4:

- No hay navegación del TAC a la línea fuente ni resaltado de sintaxis
  (prioridad 3 del plan).
- La imagen del árbol requiere Graphviz; sin él, la pestaña lo informa y el
  árbol navegable sigue disponible.
- En el primer uso, ANTLR descarga su JAR (o se usa `ANTLR4_JAR`).

## Puerta Nelson → entrega

- [x] El IDE compila una demostración completa.
- [x] La CLI imprime el mismo TAC (`test_out_01_…`, `test_out_03_…`).
- [x] Una entrada inválida muestra error y ningún TAC (`test_ide_03_…`).
- [x] Tabla extendida y frames son visibles (`test_out_04_…`, `--show-layout`).
- [x] Suite completa pasa (ver resultados).
- [x] La documentación coincide con el comportamiento.
- [x] Los commits distinguen a los cuatro integrantes (este bloque se publica
  con commits propios de Nelson).

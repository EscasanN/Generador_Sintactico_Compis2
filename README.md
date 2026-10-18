# Compiscript — compilador hasta código intermedio

Proyecto de Construcción de Compiladores para programas Compiscript (`.cps`).
La gramática combinada de ANTLR produce el lexer, el parser y el árbol
sintáctico; el análisis semántico valida tipos, ámbitos, funciones, control de
flujo, clases y arreglos; y el **Proyecto 2** agrega la generación de **código
de tres direcciones (TAC)** con reciclaje de temporales, una tabla de símbolos
extendida (direcciones, offsets, tamaños, etiquetas) y registros de activación.

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
    ↓
IDE o CLI (ambos llaman a compile_compiscript)
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
├── gui/
│   ├── app.py                       # IDE: editor, worker y pestañas
│   ├── codegen_results.py           # Vistas de TAC, tabla extendida y diagnósticos
│   ├── semantic_results.py          # Diagnósticos y tabla de símbolos por ámbito
│   └── parse_tree_view.py           # Árbol navegable
└── main.py                          # GUI y CLI

semantic_profiles/compiscript.semantic.json
docs/proyecto2/                      # Diseño TAC, arquitectura, matriz y entregas
tests/
├── antlr_mode/  codegen/  gui/  semantic/
├── cps/                             # Programas de la fase semántica
├── cps/codegen/                     # Programas y TAC esperado del Proyecto 2
└── test_main_cli.py
```

## Requisitos e instalación

- Python 3.10 o superior (probado con 3.14).
- Java 11 o superior para generar el parser de ANTLR.
- Graphviz en `PATH` (opcional; solo para la imagen del árbol en el IDE).

```powershell
git clone --branch feature/proyecto2-codegen https://github.com/EscasanN/Generador_Sintactico_Compis2.git
cd Generador_Sintactico_Compis2
python -m pip install -r requirements.txt
```

En la primera ejecución el frontend descarga ANTLR 4.13.2 y guarda el JAR y los
archivos generados en `output/antlr/` (ignorado por Git). También puede
definirse `ANTLR4_JAR` con una ruta local al JAR.

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
   - **Resumen**: estado por fase y tabla única de diagnósticos léxicos,
     sintácticos, semánticos y de generación con fase, tipo, línea y columna.

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
```

Códigos de salida:

| Código | Significado |
|---:|---|
| `0` | Compilación aceptada y TAC verificado. |
| `1` | Rechazo léxico, sintáctico, semántico o de generación de código. |
| `2` | Error de lectura/escritura, configuración o dependencia (Java, gramática). |

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

La batería de casos `.cps` del Proyecto 2 está en
[tests/cps/codegen](tests/cps/codegen/README.md): un programa válido por dominio
de la matriz, programas inválidos por fase y TAC esperado (golden) para casos
representativos.

## Demostración

Ver la guía en
[docs/proyecto2/bloque4-entrega.md](docs/proyecto2/bloque4-entrega.md#guía-de-demostración).
Programas preparados:

- válido completo: `tests/cps/codegen/validos/DEMO-completa.cps`;
- fallido: `tests/cps/codegen/invalidos/DEMO-fallida.cps`.
- regresiones del cierre y guía ampliada:
  [AUDITORIA_FINAL.md](docs/proyecto2/AUDITORIA_FINAL.md).

## Documentación

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

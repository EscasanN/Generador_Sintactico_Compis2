# Compiscript — frontend y análisis semántico

Proyecto de Construcción de Compiladores enfocado en analizar programas
Compiscript (`.cps`). La gramática combinada de ANTLR produce el lexer, el
parser y el árbol sintáctico; una segunda fase ejecuta acciones semánticas
declarativas para validar tipos, ámbitos, funciones, control de flujo, clases y
arreglos.

La versión presentada y calificada con **100/100** permanece disponible en la
etiqueta Git `entrega-semantica-100`. La rama actual elimina los generadores
históricos que ya no forman parte del flujo de trabajo.

## Flujo

```text
programa.cps
    ↓
Compiscript.g4
    ↓
Lexer y Parser de ANTLR
    ↓
árbol sintáctico común
    ↓
compiscript.semantic.json
    ↓
diagnósticos + tabla de símbolos + ACCEPT/REJECT
```

La semántica solo se ejecuta cuando el análisis sintáctico termina sin errores.
Los warnings no rechazan el programa; los diagnósticos de severidad `error` sí.

## Estructura

```text
src/
├── antlr_mode/
│   ├── grammar_info.py              # Inspección de gramáticas ANTLR
│   ├── runner.py                    # Generación, caché y ejecución
│   ├── parse_tree.py                # Árbol independiente del runtime
│   └── parse_tree_visualizer.py     # Imagen Graphviz del árbol
├── compiscript/grammar/
│   └── Compiscript.g4               # Gramática oficial
├── semantic/                        # Tipos, símbolos, acciones y adaptador
├── gui/                             # IDE de Compiscript
└── main.py                          # GUI y CLI

semantic_profiles/
└── compiscript.semantic.json        # Enlace gramática → acciones semánticas

tests/
├── antlr_mode/
├── cps/                             # Programas válidos, inválidos y warnings
├── gui/
└── semantic/
```

## Requisitos

- Python 3.10 o superior.
- Java 11 o superior para generar el parser de ANTLR.
- Graphviz instalado y disponible en `PATH` para la imagen del árbol.

```powershell
python -m pip install -r requirements.txt
```

En el primer análisis, el frontend obtiene ANTLR 4.13.2 y guarda el JAR y los
archivos generados en `output/antlr/`, que está ignorado por Git. También puede
definirse `ANTLR4_JAR` con una ruta local.

## Uso

### Interfaz gráfica

```powershell
python -m src.main
```

La GUI permite crear, abrir, editar y guardar `.cps`; muestra el árbol como
imagen y vista navegable, los diagnósticos semánticos y la tabla de símbolos por
ámbito.

### Terminal

Análisis sintáctico y semántico:

```powershell
python -m src.main --cps tests/cps/demostracion-valida.cps
```

Solo sintaxis, útil para aislar errores del parser:

```powershell
python -m src.main --cps tests/cps/demostracion-valida.cps --syntax-only
```

Los códigos de salida son:

- `0`: programa aceptado;
- `1`: programa rechazado por sintaxis o semántica;
- `2`: error de configuración o lectura.

## Pruebas

Suite completa:

```powershell
python -m pytest tests -q
```

Programas de demostración:

```powershell
python -m pytest tests/semantic/test_cps_programs.py -vv
```

Solo warnings:

```powershell
python -m pytest tests/semantic/test_cps_programs.py -vv -k warning
```

Consulte [tests/cps/README.md](tests/cps/README.md) para ejecutar casos
individuales y [docs/phase3/README.md](docs/phase3/README.md) para la
documentación del análisis semántico.

## Perfil semántico

`semantic_profiles/compiscript.semantic.json` contiene únicamente datos y
nombres de acciones permitidas. Su fingerprint vincula el perfil con la fuente
normalizada de `Compiscript.g4`; si la gramática cambia intencionalmente, el
perfil debe revisarse y actualizarse junto con sus pruebas.

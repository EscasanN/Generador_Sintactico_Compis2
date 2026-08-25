# Proyecto de Compiladores — YALex y YAPar

**Curso:** Construcción de Compiladores

**Universidad:** Universidad del Valle de Guatemala

**Lenguaje:** Python 3.x

> **Estado:** las fases léxica y sintáctica constituyen la base estable. El IDE
> conserva el modo YALex + YAPar y agrega un modo ANTLR capaz de cargar gramáticas
> combinadas `.g4` sin modificar el código. El análisis semántico todavía está
> planificado.

---

## Descripción

Implementación de un generador completo de analizadores léxicos (**YALex**) y
sintácticos (**YAPar**) con una interfaz gráfica tipo IDE. El modo original toma
una especificación de tokens (`.yal`) y una gramática libre de contexto
(`.yapar`), construye los autómatas y tablas de parseo, y analiza cadenas con
tres métodos simultáneamente. El modo adicional genera y ejecuta automáticamente
Lexer y Parser de Python a partir de una gramática ANTLR `.g4`.

```
.yal  →  YALex  →  Tokens
.yapar →  YAPar  →  LR(0)  →  SLR(1) / LALR / LL(1)  →  Análisis de cadenas
```

### Algoritmos implementados

| Componente | Algoritmo / Técnica |
|------------|---------------------|
| RE → NFA | Construcción de Thompson |
| NFA → DFA | Construcción de subconjuntos |
| DFA → DFA mínimo | Algoritmo de Hopcroft |
| Autómata LR(0) | Cierre e items LR(0) |
| Tabla SLR(1) | FOLLOW sets + LR(0) |
| Tabla LALR | Items LR(1) fusionados por core LR(0) |
| Tabla LL(1) | FIRST / FOLLOW sets |
| Árbol de derivación | Construcción durante shift/reduce/expand |

---

## Estructura del proyecto

```
Generador_Sintactico/
├── src/
│   ├── main.py                  # Punto de entrada (GUI / CLI / modo léxico)
│   ├── gui/
│   │   └── app.py               # IDE PyQt6
│   ├── antlr_mode/
│   │   ├── grammar_info.py      # Inspección de gramáticas .g4
│   │   └── runner.py            # Generación, caché y ejecución ANTLR
│   ├── lexer/
│   │   ├── scanner.py           # Lectura del archivo .yal
│   │   ├── regex_parser.py      # Parser de expresiones regulares
│   │   ├── resolver.py          # Resolución de definiciones
│   │   ├── nfa.py               # Construcción de Thompson (RE → NFA)
│   │   ├── dfa.py               # Subconjuntos + Hopcroft (NFA → DFA mínimo)
│   │   └── codegen.py           # Generación de lexer
│   ├── parser/
│   │   ├── yapar_scanner.py     # Lectura del archivo .yapar
│   │   ├── grammar.py           # Estructura de gramática y producciones
│   │   ├── lr0.py               # Autómata LR(0)
│   │   ├── first_follow.py      # Cálculo de FIRST y FOLLOW
│   │   ├── slr1.py              # Tabla y parser SLR(1) + árbol de derivación
│   │   ├── lalr.py              # Tabla y parser LALR + árbol de derivación
│   │   ├── ll1.py               # Tabla y parser LL(1) + árbol de derivación
│   │   ├── parse_tree.py        # Nodo del árbol de derivación
│   │   ├── string_analyzer.py   # Coordinador de análisis (SLR/LALR/LL1)
│   │   └── tokenizer_bridge.py  # Integración YALex → YAPar
│   └── utils/
│       └── visualizer.py        # Generación de imágenes (Graphviz)
├── tests/
│   ├── cases/                   # Casos activos de aceptación y rechazo
│   └── legacy/                  # Fixtures heredados de fases anteriores
├── docs/
│   └── phase3/                  # Plan y decisiones para análisis semántico
├── requirements.txt
└── README.md
```

---

## Requisitos

- Python 3.10 o superior
- Java 11 o superior para generar parsers ANTLR
- [Graphviz](https://graphviz.org/download/) instalado en el sistema y en el PATH

```bash
pip install -r requirements.txt
```

---

## Uso

### Modo GUI (recomendado)

```bash
python src/main.py
```

El IDE permite:

1. Elegir entre los modos **YALex + YAPar** y **ANTLR (.g4)**.
2. Cargar archivos `.yal`, `.yapar`, `.g4` y el archivo de entrada requerido.
3. Seleccionar la regla inicial de una gramática ANTLR.
4. Editar y guardar los archivos directamente.
5. Ejecutar el análisis completo con **Ctrl+R** o el botón **Analyze**.
6. Visualizar resultados en las pestañas:

| Pestaña | Contenido |
|---------|-----------|
| **LR(0)** | Imagen del autómata LR(0) generado |
| **Tables → FIRST/FOLLOW** | Conjuntos FIRST y FOLLOW por no-terminal |
| **Tables → SLR(1)** | Tabla de parseo SLR(1) con tooltips por celda |
| **Tables → LALR** | Tabla de parseo LALR con tooltips por celda |
| **Tables → LL(1)** | Tabla de parseo LL(1) (si la gramática lo permite) |
| **Tables → Productions** | Leyenda numerada de todas las producciones |
| **Parse Tree** | Árbol de derivación por cadena aceptada |
| **Steps** | Navegador paso a paso del proceso de parseo |
| **Results** | Resumen con ACCEPT/REJECT por método y mensajes de error |

### Modo ANTLR `.g4`

1. Seleccionar **ANTLR (.g4)** en `Mode` o presionar **Open G4**.
2. Cargar una gramática combinada cuyo encabezado sea `grammar Nombre;`.
3. Elegir una regla sintáctica en `Start`.
4. Cargar el programa de entrada y presionar **Analyze**.

Durante el primer uso, el IDE descarga ANTLR 4.13.2 desde su sitio oficial y lo
guarda en `output/antlr/`, carpeta ignorada por Git. Cada parser generado también
se almacena allí usando un hash del contenido de la gramática. Para trabajar sin
descarga automática se puede definir `ANTLR4_JAR` con la ruta local del JAR.

En este modo se muestran tokens, árbol y diagnósticos de ANTLR. Las pestañas
LR(0), SLR, LALR, LL(1) y pasos continúan perteneciendo al modo YAPar y no se
eliminan ni reemplazan.

### Modo CLI

```bash
python src/main.py --cli <archivo.yal> <archivo.yapar> <entrada.txt>
```

### Modo léxico (solo YALex)

```bash
python src/main.py --lex <archivo.yal>
```

---

## Formato de archivos

### Archivo `.yal` (YALex)

```
(* Comentario *)
let digit = ['0'-'9']
let letter = ['a'-'z''A'-'Z']
let id = letter (letter | digit)*

rule tokens =
  | digit+       { return INT }
  | id           { return ID }
  | ' '          { (* skip *) }
```

### Archivo `.yapar` (YAPar)

```
/* Tokens */
%token ID NUMBER PLUS SEMICOLON
IGNORE WS

%%

/* Producciones */
expr:
    expr PLUS term
  | term
;

term:
    NUMBER
  | ID
;
```

---

## Manejo de errores

- **Errores léxicos:** columna exacta del carácter inesperado
- **Errores sintácticos:** columna, token inesperado y tokens esperados en ese estado
- **Errores en `.yapar`:** línea exacta del problema en la gramática
- **Visualización:** líneas del archivo de entrada coloreadas (verde = aceptado, rojo = rechazado)

---

## Fase 3 — Análisis semántico de Compiscript

La planificación de la siguiente fase está documentada en
[`docs/phase3/`](docs/phase3/README.md). Ya están incorporados el modo genérico
ANTLR, una gramática de ejemplo, la especificación y el scaffold; todavía no
existe la implementación del análisis semántico. El reparto concreto de archivos,
clases, funciones y pruebas está en la
[guía detallada por integrante](docs/phase3/GUIA_IMPLEMENTACION_POR_INTEGRANTE.md).

---

## Autor

| Nombre | Carné |
|--------|-------|
|        |       |

# Arquitectura — Fase 3

## Base estable

El repositorio conserva:

- `src/lexer/`: YALex, NFA, DFA y minimización;
- `src/parser/`: YAPar, LR(0), SLR, LALR, LL(1) y árbol;
- `src/gui/app.py`: IDE de las fases 1 y 2.

El modo ANTLR se agrega como frontend paralelo y no reemplaza esos módulos.

## Flujo multimodo

```text
                ┌── .yal + .yapar ──> motor propio YALex/YAPar ──┐
IDE + entrada ──┤                                                ├──> vistas
                └── .g4 + .cps + start rule ──> runtime ANTLR ───┘
                                                         │
                                      ┌──────────────────┴───────────────┐
                                      v                                  v
                             árbol visual común                 árbol nativo ANTLR
                                                                         │
                                                                         v
                                                           ParseTreeWalker + Listener
                                                                         │
                                                                         v
                                                           motor semántico configurable
```

## Dirección de dependencias

La implementación se organiza en capas que solo dependen de las inferiores:

```text
GUI y perfil Compiscript                         [Nelson, bloque 4]
                    │
                    v
adaptador ANTLR-semántica + perfil MiniCalc      [Dulce, bloque 3]
                    │
                    v
evaluador + perfiles + símbolos + acciones       [Nadissa, bloque 2]
                    │
                    v
diagnósticos + tipos + valores + expresiones     [Daniel, bloque 1]
                    │
                    v
          contratos de la base multimodo
```

Una capa puede importar únicamente la base y las capas ubicadas debajo. Ninguna
capa inferior importa la GUI, el adaptador o una implementación posterior. Esta
dirección permite que cada integrante cierre su bloque antes de que comience el
siguiente.

## `src/antlr_mode/`

### `grammar_info.py`

Inspecciona la gramática sin generar código. Produce `GrammarInfo` con ruta,
nombre, tipo y reglas de parser.

### `runner.py`

1. valida la gramática y regla inicial;
2. resuelve Java y ANTLR 4.13.2;
3. descarga el JAR en el primer uso si es necesario;
4. calcula hash de versión y contenido;
5. genera Python en `output/antlr/generated/`;
6. carga Lexer y Parser dinámicamente;
7. recolecta errores;
8. verifica consumo completo;
9. conserva la sesión necesaria para recorrer el árbol nativo;
10. convierte el árbol al modelo común para visualización.

Los generados son caché reproducible, no código fuente del proyecto.

## Árbol común

`ParseTreeNode` mantiene compatibilidad con YAPar y agrega metadatos opcionales:

- regla;
- alternativa etiquetada;
- tipo y texto de token;
- ubicación inicial y final.

El modelo común sirve para pruebas unitarias, selectores declarativos y
visualización. En la integración real, el Listener de Dulce recorre el árbol
nativo de ANTLR y relaciona cada contexto con el nodo común correspondiente.

Sus campos públicos se congelan antes del bloque de Daniel. Dulce puede corregir
la producción de metadatos en su bloque, pero no cambia la forma pública que ya
consumen Daniel y Nadissa.

## GUI

`MainWindow` conserva una sola aplicación. `AnalysisWorker` atiende YAPar y el
worker ANTLR atiende la gramática `.g4` y el fuente `.cps`. Ambos trabajan fuera
del hilo principal.

El modo determina requisitos y renderizado:

- YAPar: vistas históricas completas;
- ANTLR: edición del `.cps`, tokens, árbol visual, diagnósticos y símbolos;
- cambiar de modo no borra archivos cargados del otro flujo.

El flujo evaluado permite crear, abrir, editar y guardar `.cps`. El botón
**Compile** o **Analyze** usa todo el contenido del editor y marca **ACCEPT**
solo cuando no existen errores léxicos, sintácticos ni semánticos.

La ampliación semántica de la GUI pertenece únicamente al último bloque. Nelson
consume `analyze_semantics_with_g4`; no llama directamente al generador, al
registro de acciones ni a helpers privados del evaluador.

## Semántica genérica

Una gramática solo describe sintaxis. Para evitar código diferente por lenguaje,
se propone un perfil declarativo que asocie reglas o alternativas con acciones
registradas:

```text
árbol nativo + nombres de reglas + perfil
                    │
                    v
       ParseTreeWalker.DEFAULT.walk(...)
                    │
                    v
          SemanticTreeListener
                    │
                    v
            SemanticEvaluator
            ├── TypeSystem
            ├── SymbolTable
            ├── ExpressionActions
            ├── acciones de función/control/clase
            └── DiagnosticBag
```

El perfil no ejecuta Python arbitrario. No se permite `eval`, `exec` ni
imports configurables.

La capa se divide de esta forma:

- Daniel define diagnósticos, tipos, valores y acciones de expresiones;
- Nadissa define símbolos, perfiles, registro, acciones de sentencias y
  evaluador;
- Dulce conecta el resultado ANTLR con el evaluador y demuestra generalidad;
- Nelson proporciona el perfil Compiscript y presenta el resultado.

`SemanticEvaluator` se prueba primero con árboles manuales. Por eso Nadissa no
depende de que Dulce haya terminado el adaptador. Después, Dulce prueba el mismo
motor con una gramática real sin modificarlo.

## Adaptador ANTLR-semántica

`src/semantic/antlr_adapter.py` y `antlr_listener.py` forman el límite de
integración. La operación pública recibe gramática, archivo fuente, regla
inicial y perfil:

```text
analyze_semantics_with_g4(...)
        │
        ├── analyze_with_g4(...)
        ├── load_profile(...)
        ├── validate_profile(...)
        ├── SemanticTreeListener(...)
        └── ParseTreeWalker.DEFAULT.walk(listener, native_tree)
```

Si existen errores léxicos o sintácticos, el adaptador devuelve ese resultado y
no ejecuta semántica. La GUI recibe un paquete completo y se limita a
presentarlo. El resultado integrado se acepta solo si sintaxis y semántica están
aceptadas; la ruta `.cps` opcional se conserva en todos los diagnósticos.

## Límites

- `src/antlr_mode/` no contiene semántica Compiscript.
- el núcleo `src/semantic/`, excepto `antlr_listener.py` y `antlr_adapter.py`,
  no importa ANTLR ni PyQt6;
- `antlr_listener.py` solo importa contratos genéricos de `antlr4`, nunca clases
  generadas para Compiscript;
- `src/gui/` presenta resultados, no decide tipos o scopes.
- `src/lexer/` y `src/parser/` no se reescriben para soportar `.g4`.
- `output/` no se versiona.
- Daniel no importa módulos propiedad de Nadissa, Dulce o Nelson.
- Nadissa no importa `src/antlr_mode/` ni `src/gui/`.
- Dulce no modifica los algoritmos semánticos ya aceptados.
- Nelson no agrega acciones al motor para completar un perfil.

## Representación visual del árbol

El resultado común se transforma en nodos y aristas. La salida puede ser una
imagen Graphviz o una vista jerárquica interactiva, siempre que permita observar
la estructura padre-hijo. Un volcado de texto plano no sustituye esta salida.

La representación conserva al menos símbolo, regla o token y ubicación. Los
fallos de Graphviz producen un diagnóstico visible y no cierran el IDE.

## Dependencias

- Java 11 o superior para ejecutar el generador.
- ANTLR Tool 4.13.2, descargado o indicado mediante `ANTLR4_JAR`.
- `antlr4-python3-runtime==4.13.2`.
- Graphviz para imágenes.
- PyQt6 para el IDE.

Generador y runtime deben compartir versión.

## Seguridad y fallos

Las gramáticas se consideran entradas proporcionadas por el curso. Aun así:

- la descarga usa la URL oficial;
- los procesos se invocan con argumentos, no mediante shell;
- la generación tiene timeout;
- los errores se muestran sin cerrar el IDE;
- las cachés se encuentran bajo una ruta ignorada;
- acciones embebidas no confiables quedan fuera del alcance.

## Generalidad verificable

La base prueba:

- `Compiscript.g4` con regla `program`;
- `MiniCalc.g4` con regla `root`.

Ambas usan la misma función `analyze_with_g4`. Esta prueba debe mantenerse para
impedir acoplamiento accidental.

La generalidad semántica se comprueba además con perfiles distintos. MiniCalc
es la prueba pequeña del bloque de Dulce y Compiscript es la prueba integral del
bloque de Nelson. Ambos usan el mismo `SemanticEvaluator`.

Para calificación, la gramática oficial de Compiscript y su suite tienen
prioridad. MiniCalc demuestra generalidad, pero no sustituye los casos exigidos
por `MATRIZ_CUMPLIMIENTO.md`.

## Orden de construcción

1. Daniel entrega el núcleo sin depender de árboles ni gramáticas.
2. Nadissa entrega el motor probado con árboles manuales.
3. Dulce entrega el adaptador probado con gramáticas reales.
4. Nelson entrega la integración visual y las regresiones finales.

Cada paso se integra y congela antes de comenzar el siguiente. No existe una
segunda ronda de implementación para ninguno de los cuatro integrantes.

## Alcance y estado del producto

La Fase 3 entrega un IDE que conserva el flujo YALex + YAPar y agrega un modo
ANTLR configurable. El producto evaluado permite escribir, abrir, editar,
guardar y compilar archivos `.cps` usando una gramática `.g4`, una regla inicial
y un perfil semántico seleccionados en tiempo de ejecución.

La base multimodo previa al trabajo semántico incluye inspección de gramáticas,
selección de regla inicial, generación y caché de ANTLR, carga dinámica,
diagnósticos léxicos y sintácticos, árbol común, tokens y pruebas con
Compiscript y MiniCalc. Las capacidades pendientes o entregadas se mantienen
detalladas en `PLAN.md`; esta arquitectura describe el diseño objetivo y sus
contratos.

## Invariantes del producto

- YALex + YAPar conserva sus entradas, algoritmos, vistas y regresiones.
- ANTLR recibe `.g4`, regla inicial, perfil y fuente `.cps` sin depender de
  nombres propios de Compiscript.
- Lexer, Parser y Visitor generados se almacenan únicamente en
  `output/antlr/`, que no se versiona.
- Una segunda gramática funciona sin modificar el código Python del motor.
- Los perfiles son datos declarativos: no ejecutan `eval`, `exec` ni imports
  configurables.
- El análisis, la generación y el renderizado se ejecutan fuera del hilo de Qt.
- El árbol se presenta como nodos y aristas; un volcado de texto aislado no es
  la representación visual principal.
- `ACCEPT` requiere cero errores léxicos, sintácticos y semánticos. Los warnings
  se muestran, pero no rechazan el resultado.

## Contratos públicos congelados

`GrammarInfo` expone `path`, `name`, `kind`, `parser_rules` y
`default_start_rule`. Sus operaciones públicas son `parse_g4_info(source,
path)` e `inspect_g4(path)`.

`AntlrAnalysisResult` conserva `grammar`, `start_rule`, `tree`, el árbol nativo
o una sesión equivalente, nombres de reglas, `diagnostics`, `tokens`,
`generated_directory` y `accepted`. La operación pública es
`analyze_with_g4(grammar_path, source, start_rule=None)`.

Los consumidores usan estos contratos y no helpers privados ni clases
generadas concretas. `src/semantic/` no importa ANTLR ni PyQt6, salvo los dos
módulos explícitos de integración (`antlr_listener.py` y `antlr_adapter.py`),
y el listener nunca importa clases generadas de Compiscript.

## Flujo de aceptación

El frontend rechaza la entrada si quedan tokens sin consumir. Si existen errores
léxicos o sintácticos, devuelve el resultado del frontend y no inicia el
recorrido semántico. Después valida el perfil contra las reglas de
`GrammarInfo`, crea el `SemanticTreeListener` y ejecuta
`ParseTreeWalker.DEFAULT.walk(...)` o un Visitor equivalente.

El evaluador conserva scopes globales, de función, clase y bloque para que el
IDE pueda consultarlos. Rechaza redeclaraciones en el mismo scope, resuelve
nombres desde el scope actual hacia sus ancestros y valida argumentos
posicionales, retornos, listas, miembros, constructores y `this`. Las
condiciones de `if`, `while`, `do-while`, `for` y `switch` son booleanas;
`break` y `continue` solo son válidos dentro de bucles; `return` solo dentro de
funciones. También se diagnostican código muerto y duplicación de variables o
parámetros.

## Puertas de aceptación

Cada bloque incluye implementación, casos exitosos y fallidos, documentación y
regresión antes de habilitar el siguiente:

| Puerta | Evidencia mínima |
|---|---|
| Base → Daniel | YAPar y ANTLR pasan; contratos del árbol congelados. |
| Daniel → Nadissa | Diagnósticos, tipos, valores y expresiones pasan sin ANTLR ni GUI. |
| Nadissa → Dulce | Evaluador probado con árboles manuales y símbolos persistentes. |
| Dulce → Nelson | Listener/adaptador funciona con Compiscript y otra gramática sin cambiar el motor. |
| Nelson → entrega | IDE compila `.cps`, muestra árbol y símbolos, y pasan las regresiones. |

La evidencia completa y los identificadores `TYP-*`, `SCP-*`, `FUN-*`,
`CTL-*`, `CLS-*`, `LST-*`, `GEN-*`, `ANT-*` e `IDE-*` se mantienen en
`MATRIZ_CUMPLIMIENTO.md`. Las pruebas mínimas de entrega son:

```text
python -m pytest tests/antlr_mode -q
python -m pytest tests/semantic -q
python -m pytest tests/gui -q
python -m pytest -q
```

La suite final debe demostrar un programa `.cps` válido, otro con errores de
varias categorías, Compiscript y MiniCalc sin cambios Python, y las regresiones
de YALex + YAPar.

## Decisiones y límites conocidos

- La gramática de ejemplo no es una dependencia del motor ni necesariamente la
  gramática oficial definitiva.
- Los casos semánticos negativos deben tener sintaxis válida; una entrada que
  falla en el parser solo demuestra un error sintáctico.
- `foreach`, `try/catch`, herencia y `new` son capacidades no mínimas salvo que
  la gramática oficial o el profesor las vuelvan obligatorias.
- La concatenación `string + string` no se asume: solo se acepta si el sistema
  de tipos y el perfil la definen explícitamente.
- Las decisiones pendientes o confirmadas sobre gramática, tipos y perfiles se
  registran en `REGLAS_Y_DECISIONES.md`; no se resuelven implícitamente en la
  GUI.

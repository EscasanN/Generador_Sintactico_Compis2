# Bloque 3: lowering completo y pipeline de compilación

Entrega para el Bloque 4. A partir de un `.cps` aceptado, produce TAC verificado, la
tabla extendida y los registros de activación. No presenta resultados en Qt ni en la
CLI: eso lo consume Nelson mediante `compile_compiscript`.

## Archivos

| Archivo | Contenido |
|---|---|
| `src/codegen/generator.py` | `CompiscriptCodeGenerator`: despacho por `rule_name`/`alternative`, alcanzabilidad, prepaso de procedimientos y `GeneratedProgram`. `ProgramExpressionLowerer` extiende `ExpressionLowerer` de Daniel solo en las alternativas de este bloque. |
| `src/codegen/statements.py` | Declaraciones, `const`, `x = e;`, sentencias de expresión, `print` y la conversión implícita int→float. |
| `src/codegen/control_flow.py` | if/else, while, do-while, las 4 formas de `for`, foreach, switch, break/continue y try/catch. |
| `src/codegen/callables.py` | Procedimientos, parámetros ocultos, llamadas, `return`, recursión, closures y acceso a variables capturadas. |
| `src/codegen/objects.py` | `new`, constructores (también el implícito), inicializadores de campo, `this`, campos, métodos, herencia y listas. |
| `src/codegen/results.py` | `IntermediateCodeResult`, `CompilationResult` y `program_statistics`. |
| `src/codegen/pipeline.py` | `compile_compiscript`, `generate_intermediate_code` y las constantes `GRAMMAR_PATH`, `PROFILE_PATH` y `START_RULE`. |
| `tests/codegen/conftest.py` | Fixture `generate_tac(source)`: genera un programa y exige `IRVerifier` sin diagnósticos (ver "Excepciones"). |

## Uso desde el pipeline

```python
from src.codegen.pipeline import compile_compiscript

result = compile_compiscript(source, "programa.cps")
if result.accepted:
    print(result.tac)                                      # TAC verificado
    tabla = result.intermediate_result.symbol_layouts.rows()  # tabla extendida
    frames = result.intermediate_result.activation_records    # global + uno por procedimiento
    stats = result.intermediate_result.statistics
else:
    result.failed_stage            # "syntax" | "semantic" | "codegen"
    result.syntax_result.diagnostics, result.semantic_result, result.intermediate_result
```

El orden es estricto:

1. Sintaxis.
2. Semántica, solo si la sintaxis pasa.
3. Hechos y layouts.
4. Generación.
5. `IRVerifier`.
6. `format_program`.

Un error de sintaxis o de semántica deja `intermediate_result = None`.

## Contrato público

**`compile_compiscript(source, source_path=None, *, grammar_path=GRAMMAR_PATH, profile_path=PROFILE_PATH) -> CompilationResult`**
envuelve `analyze_semantics_with_g4` sin cambiarlo. Es la única API que necesitan la
CLI y el IDE.

**`CompilationResult`** (inmutable):

- campos `syntax_result`, `semantic_result`, `intermediate_result` y `source_path`;
- propiedades `accepted`, `failed_stage` y `tac` (cadena vacía si alguna fase falla);
- rechaza construirse con un `intermediate_result` si la sintaxis o la semántica
  fallaron.

**`IntermediateCodeResult`** (inmutable):

- `program`, `text`, `diagnostics`, `layouts` (`RuntimeLayouts` finalizados con los
  slots de temporales) y `statistics`. Las estadísticas son `instructions`,
  `procedures`, `labels`, `temporaries_created` y `temporary_peak`.
- Propiedades:
  - `symbol_layouts`;
  - `activation_records`: el frame `global` primero;
  - `accepted`: hay programa y texto, y no hay diagnósticos.
- **Invariante:** con diagnósticos no hay programa ni texto. Nunca se publica TAC
  parcial.

**`generate_intermediate_code(semantic_result, tree)`**: la generación aislada para un
análisis aceptado. Lanza `ValueError` si el análisis no fue aceptado.

**`CompiscriptCodeGenerator(facts).generate(root) -> GeneratedProgram(program, layouts, global_temporary_peak)`**:
la API de bajo nivel que usan las pruebas.

**Errores.** `CodegenError`, `LayoutError` y `MissingFactError` se convierten en un
`IRDiagnostic`. Cualquier otra excepción es un defecto: se propaga y nunca se acepta.

| Código | Causa |
|---|---|
| `IRGEN-UNSUPPORTED-NODE` | Alternativa sin handler o construcción no soportada (acceso estático `C.campo`, clase usada como valor). |
| `IRGEN-BREAK-OUTSIDE-LOOP` / `IRGEN-CONTINUE-OUTSIDE-LOOP` | `break`/`continue` sin bucle en el procedimiento actual. La semántica lo acepta dentro de una función declarada en un bucle. |
| `IRGEN-ENV-UNAVAILABLE` | La función actual no recibe un `env` con el que alcanzar el entorno de una closure. |
| `IRGEN-THIS-UNAVAILABLE` | `this` o un miembro sin `this` fuera de un método o constructor (por ejemplo, en una función anidada en un método). |
| `IRGEN-VOID-VALUE` | Una llamada void usada como valor. |
| `IRGEN-MISSING-FACT` / `-SYMBOL` / `-FRAME` / `-LAYOUT` / `-LOCATION` | Falta un hecho de los bloques 1 o 2. |
| `IRGEN-LAYOUT` | El modelo de memoria rechazó un frame (por ejemplo, menos slots que el pico). |
| `IR-*` | Diagnósticos de `IRVerifier` (Bloque 1). |

## Convenciones de traducción

| Construcción | TAC |
|---|---|
| `let`/`const x = e` | `x = v`. Una constante se copia una sola vez. Sin inicializador no se emite nada (no se inventa un valor). |
| int → float implícito | Una constante se convierte al compilar (`2` → `2.0`). Otro valor usa `t = cast float v` en declaraciones, asignaciones, argumentos, retornos, elementos de lista y operaciones mixtas. |
| `print(e)` | `param v` / `call print, 1` (runtime abstracto). |
| if / while / do-while / for | Plantillas de `DISENO_TAC.md`. `continue` va a la condición (while, do-while) o a la actualización (for). |
| foreach | `tN = list_len l`, `ti = 0`, `foreach_cond: tc = ti < tN`, `x = list_get l, ti`, `foreach_next: ti = ti + 1`. `continue` va a `foreach_next`. |
| switch | El discriminante se evalúa una vez; luego `tc = t0 == caso` / `if tc goto Lcase` en orden y caída entre casos. |
| try/catch | `try_begin Lcatch` … `try_end`, `goto Lend`, `Lcatch: catch err` … (IR de alto nivel). |
| Función | `procedure fn_f(this?, env?, params…)`; se agrega un `return` final si el fin es alcanzable. |
| Llamada directa | `param a…` / `t = call fn_f, n`. |
| Función anidada con entorno | `c = closure fn_f.g, e` / `param a…` / `t = closure_call c, n`. |
| Función como valor | `t = closure fn_f.g, e`; una función global usa `closure fn_g, null`. |
| `new C(a)` | `t = object_new C, size` / `param t` / `param a` / `call C.constructor, n+1`. |
| Método | `param recv` / `param a…` / `t = call Clase.m, n+1`. |
| Campos | `t = field_get o, off` / `field_set o, off, v`. Un nombre de miembro sin `this` dentro de la clase usa `this`. |
| Listas | `t = list_new n` + `list_set t, i, e` en orden; `list_get a, i`; `a[i] = v` emite `list_set a, i, v`. |

Ejemplo real (`tests/cps/validos/FUN-04-closure.cps`):

```text
procedure fn_exterior():
    t0 = env_new 16
    env_set t0, 0, 10
    t1 = closure fn_exterior.interior, t0
    t2 = closure_call t1, 0
    release t1
    return t2

procedure fn_exterior.interior(parameter:fn_exterior.interior[32]@env):
    t0 = env_get parameter:fn_exterior.interior[32]@env, 0:0
    t1 = t0 + 1
    release t0
    return t1
```

Ejemplo real (`tests/cps/validos/CLS-01-miembros.cps`):

```text
global:
    t0 = object_new Punto, 8
    param t0
    param 2
    param 3
    call Punto.constructor, 3
    static[0]@punto = t0
    release t0
    ...
procedure Punto.constructor(parameter:Punto.constructor[32]@this, parameter:Punto.constructor[40]@x, parameter:Punto.constructor[44]@y):
    field_set parameter:Punto.constructor[32]@this, 0, parameter:Punto.constructor[40]@x
    field_set parameter:Punto.constructor[32]@this, 4, parameter:Punto.constructor[44]@y
    return
```

Ejemplo real de `foreach`:

```text
    t3 = static[8]@xs
    t0 = list_len t3
    t4 = 0
    foreach_cond3:
    t1 = t4 < t0
    ifFalse t1 goto foreach_end5
    static[16]@x = list_get t3, t4
    param static[16]@x
    call print, 1
    foreach_next4:
    t4 = t4 + 1
    goto foreach_cond3
    foreach_end5:
    release t1
    release t4
    release t0
    release t3
```

## Decisiones adoptadas

- **Procedimientos fuera del flujo.** Una declaración de función o clase no emite nada
  en su lugar. Primero se genera el código global y después un procedimiento por
  función, método y constructor, en orden fuente. Esto incluye las funciones anidadas
  y las que están en código inalcanzable. Las etiquetas vienen de la tabla de Nadissa,
  así que la recursión directa y la mutua son llamadas a la misma etiqueta.
- **Código inalcanzable.** Después de `return`, `break`, `continue` o `goto` no se emite
  nada hasta una etiqueta que sea destino de un salto. La semántica solo da un warning,
  y el TAC se produce sin ese código muerto (PIPE-03).
- **Vida de temporales entre ramas.** La condición de if/while/for, el discriminante
  del switch y el estado del foreach siguen vivos hasta la etiqueta de unión y se
  liberan ahí. En do-while, la condición se libera al salir. Si la unión es
  inalcanzable, el lease se descarta sin emitir `release`. Con esto el verificador
  nunca ve un temporal reciclado mientras otro camino lo lee.
- **Closures por referencia.** Esta decisión mejora la limitación que documentó el
  Bloque 2:
  - Una variable capturada vive en el entorno de su dueño.
  - El prólogo del dueño crea `e = env_new size`, enlaza el `env` que recibió y copia
    sus parámetros capturados.
  - Desde ese momento, el dueño lee y escribe con `env_get`/`env_set` sobre `e`, y las
    funciones internas usan el `depth:offset` de `LexicalAccess`.
  - El slot `captured` del frame se conserva por compatibilidad con el layout.
  - El puntero `e` es un temporal que vive toda la activación, por lo que no lleva
    `release`.
- **Puntero de entorno al crear una closure.** Es `e` si la función actual creó la
  función anidada. Si no, se sube desde `env` leyendo el enlace de acceso de cada
  entorno (`env_get p, parent_offset`). Nunca se usa el enlace de control.
- **Parámetros ocultos.** `this` y `env` no tienen un `Symbol` semántico: se sintetizan
  por frame con la dirección de su slot. Primero va `this`, luego `env`, luego los
  parámetros declarados. `closure_call` cuenta solo los argumentos explícitos (el
  `env` viaja dentro de la closure).
- **Métodos estáticos por (clase, nombre).** La semántica puede registrar en un
  `PropertyAccessExpr` un símbolo provisional (predeclarado) que no está en ninguna
  tabla. Por eso la etiqueta se toma de `ClassLayout.method_label(nombre)` del tipo
  estático del receptor, y los offsets de `member_offset`. No hay despacho dinámico.
- **Constructores.**
  - Una clase sin constructor recibe `C.constructor(this)` sintetizado con su propio
    frame (header + `this`).
  - Todo constructor ejecuta primero los inicializadores de campo de la clase y de sus
    bases, empezando por la base: la gramática no tiene `super` y la semántica nunca
    invoca el constructor base.
- **Orden de evaluación.** Es de izquierda a derecha. Un receptor, una base de lista o
  un índice se copian a un temporal solo cuando un operando posterior puede
  modificarlos (asignación, llamada o `new`).
- **`switch` y `break`.** `break` y `continue` pertenecen al bucle más cercano, como en
  la semántica vigente. Los casos conservan la caída.
- **Retorno faltante.** Una función no void cuyo final es alcanzable termina con un
  `return` sin valor: no se inventa uno (pregunta pendiente en `REGLAS_Y_DECISIONES.md`).

## Pruebas

```powershell
python -m pytest tests/codegen/test_statements.py tests/codegen/test_control_flow_lowering.py tests/codegen/test_callables.py tests/codegen/test_closures.py tests/codegen/test_objects.py tests/codegen/test_lists.py tests/codegen/test_pipeline.py -q   # 158 pasan
python -m pytest tests -q        # 688 pasan
```

| Archivo | Pruebas | Cubre |
|---|---:|---|
| `test_statements.py` | 15 | Declaraciones, shadowing, `const`, `print`, conversiones, código inalcanzable, nodo sin soporte y pico global. |
| `test_control_flow_lowering.py` | 17 | if/else, while, do-while, 4 formas de `for`, foreach, switch, bucles anidados, try/catch y destinos restaurados tras un error. |
| `test_callables.py` | 10 | Procedimientos, parámetros, orden de argumentos, void/valor, retornos, casts, `FUN-03-recursion.cps` y picos por frame. |
| `test_closures.py` | 8 | `FUN-04-closure.cps`, captura a 1 y 2 niveles, escritura por referencia, función escapada, llamada indirecta y recursión de una closure. |
| `test_objects.py` | 13 | `new`, constructores, campos, métodos, herencia, miembro posterior, miembros sin `this` y `demostracion-valida.cps`. |
| `test_lists.py` | 8 | Literales, `list_get`, `list_set`, índices anidados, lista float y foreach. |
| `test_pipeline.py` | 87 | Orden de fases, rechazo sin TAC, verificador y cada `.cps` existente. Los 34 válidos y de advertencias producen TAC verificado; los 38 inválidos no producen TAC. También invariantes y cobertura de la gramática. |

Casos negativos propios:

- nodo sin soporte;
- `break` y `continue` sin bucle;
- `break` dentro de una función declarada en un bucle;
- `IRGEN-ENV-UNAVAILABLE`;
- acceso estático `C.v`;
- `this` en una función anidada;
- error del verificador;
- `.cps` sintáctica y semánticamente inválidos.

Casos de la matriz: EXP-05, EXP-06, EXP-08, CTL-01…CTL-08, FUN-01, FUN-03…FUN-07
(FUN-08 integrado con el Bloque 2), CLS-02…CLS-06, LST-01…LST-04, TMP-04, TMP-05,
SYM-06, PIPE-01…PIPE-05, EXT-01, EXT-03 (ternario en `GEN-02-expresiones.cps`),
EXT-04, EXT-05, EXT-07 y EXT-08.

## Puerta Dulce → Nelson

- [x] `compile_compiscript` es la única API integral necesaria por consumidores.
- [x] Toda salida aceptada pasa `IRVerifier`. El pipeline lo ejecuta y las pruebas lo
      repiten.
- [x] Los errores previos impiden generar TAC (`intermediate_result is None`).
- [x] La matriz mínima funciona desde archivos `.cps` (`tests/cps/validos`,
      `advertencias` y `demostracion-valida.cps`).
- [x] No hay dependencias de PyQt6 en `src/codegen` (hay una prueba que lo verifica).
- [x] APIs y ejemplos documentados en este archivo.

Para Nelson:

- **Códigos de salida de la CLI:** 0 si `result.accepted`, 1 si existe
  `result.failed_stage`. Las excepciones del frontend (`AntlrModeError`,
  `SemanticAdapterError`) siguen saliendo de `analyze_semantics_with_g4` igual que
  antes.
- **Formato del TAC:** `result.tac` ya está formateado.

## Excepciones a la propiedad de archivos

- `tests/codegen/conftest.py` (Bloque 2): se agregó el fixture `generate_tac` sin
  modificar los existentes.
- `tests/codegen/test_control_flow.py` se llama `test_control_flow_lowering.py`: el
  nombre de la guía choca con `tests/semantic/test_control_flow.py`, porque las carpetas
  de pruebas no son paquetes y pytest exige nombres de módulo únicos.
- No se modificaron `Compiscript.g4`, el perfil semántico ni los módulos de los
  bloques 1 y 2.

## Limitaciones conocidas

- **Llamada a una closure hermana.** Una función que no captura nada no recibe `env`.
  Por eso no puede llamar a una función hermana que sí lo necesita: se reporta
  `IRGEN-ENV-UNAVAILABLE`. El origen es que `needs_env` se calcula solo a partir de
  variables capturadas, no de llamadas.
- **`this` dentro de funciones anidadas en métodos.** No se captura y produce
  `IRGEN-THIS-UNAVAILABLE`.
- **Acceso estático `C.campo`.** La semántica lo acepta, pero produce
  `IRGEN-UNSUPPORTED-NODE`.
- **try/catch.** Es IR de alto nivel: el verificador no modela el salto implícito a
  `Lcatch`. Puede fallar la verificación (con diagnóstico, nunca con TAC aceptado) si
  el bloque `try` siempre transfiere control y la unión libera un temporal externo.
- **Métodos.** Se resuelven por el tipo estático del receptor; no hay vtables.
- **Conversiones.** int→float en aritmética mixta se hace con `cast`; no hay otras
  conversiones implícitas.

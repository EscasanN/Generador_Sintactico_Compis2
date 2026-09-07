# Guía completa de la entrega y defensa

> Estado verificado: 7 de septiembre de 2026. La batería completa termina con
> **385 pruebas aprobadas** y la evidencia ejecutable de Compiscript contiene
> **69 programas `.cps`**.

## 1. Qué se construyó

El repositorio conserva el generador original de analizadores YALex + YAPar y
agrega un flujo paralelo basado en ANTLR para Compiscript. La entrega actual
puede:

1. cargar una gramática ANTLR combinada `.g4`;
2. generar dinámicamente Lexer y Parser Python;
3. analizar un programa fuente `.cps`;
4. producir tokens y árbol sintáctico;
5. recorrer el árbol nativo mediante un Listener genérico;
6. ejecutar reglas semánticas configuradas en un perfil JSON;
7. acumular diagnósticos con categoría, línea y columna;
8. construir y conservar una tabla de símbolos por entorno;
9. mostrar todo desde la GUI o imprimirlo desde la CLI.

En esta entrega, **compilar** significa ejecutar análisis léxico, sintáctico y
semántico. No significa ejecutar las instrucciones `print`, generar bytecode ni
producir código máquina.

## 2. Diferencia entre los archivos importantes

| Archivo | Qué contiene | Quién lo consume |
|---|---|---|
| `.g4` | La sintaxis del lenguaje: tokens, reglas y forma del árbol. | ANTLR y `src/antlr_mode/`. |
| `.cps` | Un programa escrito en Compiscript. | El Lexer y Parser generados; después, el analizador semántico. |
| `.semantic.json` | La relación entre nodos de la gramática y acciones semánticas permitidas. | `src/semantic/profile.py`, Listener y evaluador. |
| `.yal` | Especificación léxica del flujo histórico. | Motor YALex propio. |
| `.yapar` | Gramática del flujo histórico. | Motor YAPar propio. |

La idea clave para explicar al profesor es:

> La gramática dice qué forma tiene un programa. El perfil semántico dice qué
> significa cada forma. El archivo `.cps` es el programa concreto que se valida.

## 3. Flujo completo de un `.cps`

```text
GUI o CLI
   │
   ├── Compiscript.g4
   ├── programa.cps
   ├── regla inicial: program
   └── compiscript.semantic.json
            │
            v
   inspect_g4: valida nombre y descubre reglas
            │
            v
   ANTLR 4.13.2 genera Lexer + Parser Python
            │
            v
   Lexer → tokens → Parser → árbol nativo ANTLR
            │                         │
            │                         └── conversión a ParseTreeNode común
            v
   errores léxicos/sintácticos o consumo completo de entrada
            │
            ├── si hay error: REJECT y no se ejecuta semántica
            │
            v
   cargar y validar perfil semántico
            │
            v
   ParseTreeWalker → SemanticTreeListener
            │
            v
   SemanticEvaluator + acciones registradas
            │
            ├── tipos y expresiones
            ├── scopes y símbolos
            ├── funciones y retornos
            ├── control de flujo
            ├── clases, objetos y herencia
            └── listas y reglas generales
            │
            v
   diagnósticos + tabla de símbolos + estadísticas
            │
            v
   ACCEPT si no existe ningún ERROR
```

### 3.1 Inspección de la gramática

[`src/antlr_mode/grammar_info.py`](../../src/antlr_mode/grammar_info.py) lee el
encabezado `grammar Nombre;`, comprueba que el archivo se llame `Nombre.g4` y
descubre las reglas de parser. La primera regla puede actuar como regla inicial,
aunque para Compiscript se selecciona explícitamente `program`.

### 3.2 Generación y caché de ANTLR

[`src/antlr_mode/runner.py`](../../src/antlr_mode/runner.py) realiza el frontend:

1. verifica que la gramática sea combinada;
2. comprueba que Java esté disponible;
3. calcula una clave usando la versión de ANTLR y el contenido de la gramática;
4. busca el Lexer y Parser correspondientes en `output/antlr/generated/`;
5. si ambos existen, reutiliza esa caché sin necesitar localizar el JAR;
6. únicamente cuando falta la caché, localiza ANTLR 4.13.2 —variable
   `ANTLR4_JAR`, carpeta `tools`, caché local o descarga— y valida su huella
   SHA-256;
7. ejecuta el JAR con `-Dlanguage=Python3 -visitor -no-listener` para generar
   Lexer y Parser Python;
8. importa dinámicamente las clases generadas;
9. ejecuta Lexer y Parser con listeners de errores propios;
10. verifica que no queden tokens después de la regla inicial;
11. conserva el árbol nativo y crea el árbol común para visualización.

Los archivos generados son caché reproducible y no forman parte del código
fuente versionado.

### 3.3 Árbol nativo y árbol común

ANTLR produce el árbol que recorre `ParseTreeWalker`. Al mismo tiempo,
[`src/parser/parse_tree.py`](../../src/parser/parse_tree.py) representa cada nodo
como `ParseTreeNode` con:

- nombre de regla;
- alternativa etiquetada;
- tipo y texto del token;
- hijos;
- línea y columna inicial/final.

El árbol nativo permite usar el Listener real de ANTLR. El árbol común permite
visualizar, probar y resolver selectores sin importar una clase generada de
Compiscript en el núcleo semántico.

### 3.4 Frontera sintaxis-semántica

La función pública
`analyze_semantics_with_g4` está en
[`src/semantic/antlr_adapter.py`](../../src/semantic/antlr_adapter.py). Su orden
es deliberado:

1. llama a `analyze_with_g4`;
2. si la sintaxis falla, devuelve el resultado sin ejecutar semántica;
3. carga el perfil;
4. verifica identidad y reglas disponibles;
5. crea `SemanticTreeListener`;
6. recorre el árbol nativo;
7. devuelve sintaxis y semántica en un solo `SemanticRunResult`.

Esto evita reportar errores semánticos inventados sobre un árbol sintáctico
inválido.

## 4. Qué es `semantic_profiles` y por qué hay dos JSON

La carpeta [`semantic_profiles/`](../../semantic_profiles) contiene dos perfiles:

| Perfil | Gramática correspondiente | Propósito |
|---|---|---|
| `compiscript.semantic.json` | `src/compiscript/grammar/Compiscript.g4` | Implementación completa usada en la entrega. |
| `minicalc.semantic.json` | `tests/antlr_mode/fixtures/MiniCalc.g4` | Prueba pequeña de que el motor no está codificado solo para Compiscript. |

No son dos versiones rivales de Compiscript. Cada perfil pertenece a una
gramática diferente. MiniCalc demuestra generalidad; Compiscript es el perfil
que se presenta y evalúa.

### 4.1 Qué declara un perfil

Un binding del JSON indica:

- regla y alternativa del árbol;
- acción semántica registrada;
- momento de ejecución;
- datos que se toman del nodo o de sus hijos.

Ejemplo conceptual para una suma:

```json
{
  "rule": "additiveExpr",
  "alternative": "AddExpr",
  "actions": [
    {
      "name": "expression.binary",
      "arguments": {
        "operator": "+",
        "left": {"$select": "child", "index": 0},
        "right": {"$select": "child", "index": 2}
      }
    }
  ]
}
```

El perfil no ejecuta código Python arbitrario. Los nombres deben existir en la
lista segura de [`src/semantic/action_registry.py`](../../src/semantic/action_registry.py).
No se usa `eval`, `exec` ni imports definidos desde JSON.

### 4.2 Fases de las acciones

[`src/semantic/profile.py`](../../src/semantic/profile.py) admite tres fases:

| Fase | Momento | Ejemplo |
|---|---|---|
| `enter` | Antes de visitar los hijos. | Abrir una función o clase. |
| `after_child` | Inmediatamente después de un hijo específico. | Tipar el iterador de `foreach` antes de entrar a su bloque; abrir el scope de `catch`. |
| `exit` | Después de evaluar todos los hijos. | Calcular una expresión, validar retorno o cerrar scope. |

### 4.3 Protección contra perfiles incompatibles

Los dos perfiles registran nombre y SHA-256 normalizado de su `.g4`. El
adaptador comprueba ambos antes de ejecutar acciones. Si alguien reemplaza
`Compiscript.g4` por otra gramática con reglas o posiciones diferentes, el
perfil falla de forma controlada en lugar de aplicar selectores incorrectos.

## 5. Cómo funciona el motor semántico

### 5.1 Listener y evaluador

[`src/semantic/antlr_listener.py`](../../src/semantic/antlr_listener.py) recibe
eventos reales de `ParseTreeWalker` y mantiene una pila de nodos activos. Para
cada nodo resuelve su binding y ejecuta las acciones `enter`, `after_child` y
`exit`.

[`src/semantic/evaluator.py`](../../src/semantic/evaluator.py) contiene el
contexto de una corrida:

- tabla de símbolos;
- diagnósticos;
- resultados de nodos;
- pila de funciones;
- pila de clases;
- pila de bucles;
- clases conocidas;
- símbolos predeclarados;
- servicio de expresiones.

Al terminar o abortar un recorrido, restaura el scope global y limpia las pilas
contextuales. Así una compilación fallida no contamina la siguiente.

### 5.2 Prepass global

Al entrar a `program`, la acción `program.predeclare` de
[`src/semantic/actions/composition.py`](../../src/semantic/actions/composition.py)
hace una primera pasada de interfaces:

1. reúne las declaraciones globales de clase y función;
2. declara clases respetando dependencias de herencia;
3. registra campos y firmas de métodos;
4. registra firmas de funciones globales;
5. después permite el recorrido normal de los cuerpos.

Gracias a esto funcionan:

- llamadas a una función declarada posteriormente;
- recursión directa;
- recursión mutua entre funciones globales;
- una superclase escrita después de su subclase;
- métodos que usan campos o métodos declarados posteriormente.

Las declaraciones duplicadas se rechazan y su cuerpo no reutiliza ni modifica
accidentalmente el símbolo de la primera declaración.

### 5.3 Tipos y expresiones

[`src/semantic/types.py`](../../src/semantic/types.py) define:

- `boolean`, `integer`, `float`, `string` y `null`;
- arreglos;
- funciones;
- clases y superclases;
- `UNKNOWN` para información aún no determinada;
- `ERROR` para evitar diagnósticos en cascada.

También define compatibilidad:

- coincidencia exacta;
- promoción `integer → float`;
- subclase → clase ancestro;
- `null → clase` y `null → arreglo`;
- arreglos y funciones invariantes.

[`src/semantic/expression_actions.py`](../../src/semantic/expression_actions.py)
valida literales, operadores unarios y binarios, asignación, ternario, listas e
índices. Incluye:

- `+`, `-`, `*`, `/` y `%` numéricos;
- `string + string`;
- `&&`, `||` y `!` booleanos;
- comparaciones entre tipos compatibles;
- tipo común de listas;
- índices exclusivamente `integer`.

### 5.4 Scopes y tabla de símbolos

[`src/semantic/symbol_table.py`](../../src/semantic/symbol_table.py) conserva
cuatro tipos de entorno:

- `global`;
- `function`;
- `class`;
- `block`.

Cada `Scope` conoce a su padre, hijos y símbolos. La resolución empieza en el
scope actual y sube hacia los ancestros, por lo que se obtiene siempre la
declaración visible más cercana. El shadowing en un hijo es válido; la
redeclaración en el mismo scope se rechaza.

Los scopes cerrados se conservan para que la GUI pueda mostrar la tabla completa
después del análisis.

### 5.5 Acciones por responsabilidad

| Archivo | Responsabilidad principal |
|---|---|
| [`actions/declarations.py`](../../src/semantic/actions/declarations.py) | Variables, constantes, parámetros, resolución de identificadores y scopes. |
| [`actions/callables.py`](../../src/semantic/actions/callables.py) | Firmas, llamadas, parámetros, retornos, funciones y closures. |
| [`actions/control_flow.py`](../../src/semantic/actions/control_flow.py) | Condiciones booleanas, bucles, `break`, `continue`, `foreach` y código inalcanzable. |
| [`actions/classes.py`](../../src/semantic/actions/classes.py) | Clases, campos, métodos, `this`, construcción, miembros y herencia. |
| [`actions/composition.py`](../../src/semantic/actions/composition.py) | Listas de argumentos/elementos, adaptadores de árbol, asignaciones y prepass. |
| [`diagnostics.py`](../../src/semantic/diagnostics.py) | Severidad, categoría, mensaje y ubicación. |
| [`results.py`](../../src/semantic/results.py) | Resultado semántico público e inmutable. |

## 6. Funcionalidades demostrables y evidencia

La fuente detallada de requisitos es
[`MATRIZ_CUMPLIMIENTO.md`](MATRIZ_CUMPLIMIENTO.md). Los programas canónicos están
en [`tests/cps/`](../../tests/cps/README.md).

| ID | Qué demuestra | Programa válido | Programa inválido |
|---|---|---|---|
| TYP-01 | Aritmética con `integer`/`float`. | `validos/TYP-01-aritmetica.cps` | `invalidos/TYP-01-aritmetica-booleana.cps` |
| TYP-02 | Lógica exclusivamente booleana. | `validos/TYP-02-logica.cps` | `invalidos/TYP-02-logica-no-booleana.cps` |
| TYP-03 | Comparaciones compatibles. | `validos/TYP-03-comparaciones.cps` | `invalidos/TYP-03-comparacion-incompatible.cps` |
| TYP-04 | Asignación compatible. | `validos/TYP-04-asignacion.cps` | `invalidos/TYP-04-asignacion-incompatible.cps` |
| TYP-05 | Constante inicializada. | `validos/TYP-05-constante.cps` | `invalidos/TYP-05-constante-sin-inicializar.cps` |
| TYP-06 | Listas/campos con tipos válidos. | `validos/TYP-06-estructuras.cps` | `invalidos/TYP-06-estructura-incompatible.cps` |
| SCP-01 | Resolución local y global más cercana. | `validos/SCP-01-resolucion.cps` | `invalidos/SCP-01-no-declarada.cps` |
| SCP-02 | Shadowing y rechazo de redeclaración. | `validos/SCP-02-shadowing.cps` | `invalidos/SCP-02-redeclaracion.cps` |
| SCP-03 | Acceso y salida de bloques anidados. | `validos/SCP-03-bloques-anidados.cps` | `invalidos/SCP-03-fuera-de-alcance.cps` |
| SCP-04 | Entornos global, función, clase y bloque. | `validos/SCP-04-entornos.cps` | `invalidos/SCP-04-fuga-de-bloque.cps` |
| FUN-01 | Aridad y tipos posicionales. | `validos/FUN-01-argumentos.cps` | `invalidos/FUN-01-argumentos-incorrectos.cps` |
| FUN-02 | Tipo de retorno. | `validos/FUN-02-retorno.cps` | `invalidos/FUN-02-retorno-incompatible.cps` |
| FUN-03 | Llamada adelantada y recursión. | `validos/FUN-03-recursion.cps` | `invalidos/FUN-03-llamada-no-funcion.cps` |
| FUN-04 | Función anidada y closure. | `validos/FUN-04-closure.cps` | `invalidos/FUN-04-captura-inexistente.cps` |
| FUN-05 | Nombres de función únicos. | `validos/FUN-05-nombres-distintos.cps` | `invalidos/FUN-05-funcion-duplicada.cps` |
| CTL-01 | Condiciones de `if`, `while`, `do-while`, `for` y `switch`. | `validos/CTL-01-condiciones.cps` | Cinco archivos `invalidos/CTL-01-*.cps` |
| CTL-02 | `break`/`continue` dentro de bucles y `foreach`. | `validos/CTL-02-bucles.cps` | `invalidos/CTL-02-break-*.cps` y `CTL-02-continue-*.cps` |
| CTL-03 | `return` dentro de función. | `validos/CTL-03-return.cps` | `invalidos/CTL-03-return-global.cps` |
| CTL-04 | Variable de `catch` tipada y local. | `validos/CTL-04-catch.cps` | `invalidos/CTL-04-catch-fuera-de-alcance.cps` |
| CLS-01 | Existencia de campos y métodos. | `validos/CLS-01-miembros.cps` | `invalidos/CLS-01-miembro-inexistente.cps` |
| CLS-02 | Constructor explícito o implícito correcto. | `validos/CLS-02-constructor.cps` | `invalidos/CLS-02-constructor-incorrecto.cps` |
| CLS-03 | Uso de `this` dentro de clase. | `validos/CLS-03-this.cps` | `invalidos/CLS-03-this-fuera-de-clase.cps` |
| CLS-04 | Herencia, miembros heredados y superclase. | `validos/CLS-04-herencia.cps` | `invalidos/CLS-04-superclase-desconocida.cps` |
| LST-01 | Lista homogénea. | `validos/LST-01-lista-homogenea.cps` | `invalidos/LST-01-lista-heterogenea.cps` |
| LST-02 | Índice `integer`. | `validos/LST-02-indice-entero.cps` | `invalidos/LST-02-indice-no-entero.cps` |
| GEN-01 | Detección de código inalcanzable. | `validos/GEN-01-flujo-alcanzable.cps` | `advertencias/GEN-01-codigo-inalcanzable.cps` |
| GEN-02 | Expresiones con sentido semántico. | `validos/GEN-02-expresiones.cps` | `invalidos/GEN-02-operacion-sin-sentido.cps` |
| GEN-03 | Nombres de variables/parámetros no duplicados. | `validos/GEN-03-nombres.cps` | Dos archivos `invalidos/GEN-03-*.cps` |

Detalles especiales:

- El inválido de TYP-05 falla en sintaxis porque la gramática exige `=` e
  inicializador. La regla semántica de constantes se prueba además de forma
  unitaria.
- GEN-01 produce `WARNING`, por lo que el archivo sigue en `ACCEPT`.
- `switch` exige condición booleana porque así se interpretó literalmente el
  enunciado evaluado.
- `validos/EXT-01-endurecimiento.cps` reúne `%`, concatenación, `null`, herencia,
  recursión mutua, `foreach` y `catch`.

## 7. Cómo decide ACCEPT o REJECT

Primero hay una diferencia importante entre **un programa rechazado** y **una
configuración que no puede ejecutarse**. Si el perfil no existe, su JSON es
inválido, referencia reglas inexistentes o su nombre/fingerprint no corresponde
a la gramática, el adaptador lanza `SemanticAdapterError`. En la CLI eso se
muestra como `ERROR` y termina con código `2`; no se etiqueta como `REJECT`,
porque todavía no existe un resultado semántico válido con el cual juzgar al
programa.

Una vez que gramática y perfil forman una configuración válida, el resultado
integrado es `ACCEPT` únicamente cuando:

1. el Lexer no produjo errores;
2. el Parser no produjo errores;
3. la regla inicial consumió toda la entrada;
4. el Listener terminó y produjo un resultado semántico;
5. no existe ningún diagnóstico semántico con severidad `ERROR`.

Un `WARNING`, como código inalcanzable, se muestra pero no rechaza el programa.

Las categorías semánticas visibles son:

| Categoría | Ejemplos |
|---|---|
| `type` | Operadores o asignaciones incompatibles. |
| `scope` | Identificador no declarado o redeclaración. |
| `function` | Aridad, tipos de argumentos o retorno. |
| `control_flow` | Condición no booleana, `break` o `return` fuera de contexto. |
| `class` | `this`, miembro o superclase inválida. |
| `array` | Elementos incompatibles, índice o `foreach` inválido. |
| `general` | Operador no soportado o warning de código inalcanzable. |

## 8. Flujo de la GUI

El punto de entrada es [`src/main.py`](../../src/main.py). Sin argumentos abre
[`src/gui/app.py`](../../src/gui/app.py).

### 8.1 Pasos exactos para Compiscript

Desde la raíz:

```powershell
python -m src.main
```

En la ventana:

1. seleccionar **ANTLR (.g4)** en `Mode`;
2. pulsar **Open G4**;
3. abrir `src/compiscript/grammar/Compiscript.g4`;
4. verificar que `Start` indique `program`;
5. pulsar **Load Profile**;
6. abrir `semantic_profiles/compiscript.semantic.json`;
7. pulsar **Open Input**;
8. abrir un `.cps`, por ejemplo `tests/cps/demostracion-valida.cps`;
9. pulsar **Analyze** o `Ctrl+R`.

El IDE utiliza el contenido actual del editor cuando el archivo activo es el
`.cps`, incluso si todavía no se ha guardado.

### 8.2 Qué sucede dentro de la GUI

- Sin perfil, `AntlrAnalysisWorker` ejecuta solo sintaxis.
- Con perfil, `SemanticAnalysisWorker` llama al adaptador completo.
- Los workers heredan de `QThread`, por lo que generación y análisis no bloquean
  el hilo visual.
- `_render_antlr_bundle` presenta tokens, diagnósticos y árbol.
- `_render_semantic_bundle` agrega la vista navegable y el panel semántico.

[`src/gui/semantic_results.py`](../../src/gui/semantic_results.py) muestra:

- tabla de diagnósticos: severidad, categoría, línea, columna y mensaje;
- árbol de scopes y símbolos: nombre, clase de símbolo, tipo y mutabilidad.

[`src/gui/parse_tree_view.py`](../../src/gui/parse_tree_view.py) construye la
vista navegable. [`src/utils/visualizer.py`](../../src/utils/visualizer.py)
produce la imagen Graphviz.

### 8.3 Qué enseñar en pantalla

Con el programa válido:

1. `Results` debe indicar aceptación;
2. `ANTLR Tokens` debe mostrar tipo, texto, línea y columna;
3. `Parse Tree` debe mostrar imagen y pestaña `Navigable`;
4. `Semantics` no debe mostrar errores;
5. la tabla debe mostrar scopes global, clase, función y bloque.

Después abrir `demostracion-invalida.cps` y repetir. Deben aparecer las seis
familias principales sin detenerse en el primer error.

## 9. Flujo de la CLI

La forma general es:

```powershell
python -m src.main --cps SOURCE [--grammar ARCHIVO.g4] `
  [--profile PERFIL.semantic.json] [--start REGLA] [--syntax-only]
```

| Argumento | Valor predeterminado y función |
|---|---|
| `SOURCE` | Obligatorio. Archivo fuente que se analizará, normalmente `.cps`. |
| `--grammar` | Sin esta opción usa `src/compiscript/grammar/Compiscript.g4`. Si se proporciona una gramática externa y no se da perfil, el flujo pasa a solo sintaxis. |
| `--profile` | Sin `--grammar` puede sustituir el perfil de Compiscript. Junto con una gramática externa habilita semántica solo si ambos son compatibles. |
| `--start` | Sin esta opción usa la primera regla de parser descubierta; en Compiscript es `program`. |
| `--syntax-only` | Fuerza la ejecución de Lexer y Parser sin cargar ningún perfil semántico. |

`--syntax-only` y `--profile` son mutuamente excluyentes. Si se proporcionan
juntos, `argparse` rechaza los argumentos y el proceso termina con código `2`.

### 9.1 Compiscript completo con valores predeterminados

```powershell
python -m src.main --cps tests/cps/demostracion-valida.cps
```

Al no especificar otros archivos, usa:

- `src/compiscript/grammar/Compiscript.g4`;
- `semantic_profiles/compiscript.semantic.json`;
- regla inicial predeterminada `program`.

### 9.2 Forzar solo sintaxis

```powershell
python -m src.main --cps tests/cps/demostracion-valida.cps --syntax-only
```

Este comando usa la gramática predeterminada, pero omite deliberadamente el
perfil y reporta `ACCEPT — solo sintaxis (sin perfil semántico)` si Lexer y
Parser aceptan la entrada.

### 9.3 Gramática externa: solo sintaxis

```powershell
python -m src.main --cps entrada.cps `
  --grammar Otra.g4 `
  --start reglaInicial
```

Si se entrega una `.g4` externa sin perfil, el proyecto no inventa su semántica:
ejecuta Lexer y Parser, muestra diagnósticos y deja claro que fue solo sintaxis.

### 9.4 Gramática externa con perfil compatible

```powershell
python -m src.main --cps entrada.cps `
  --grammar Otra.g4 `
  --profile otra.semantic.json `
  --start reglaInicial
```

### 9.5 Códigos de salida

| Código | Significado |
|---:|---|
| `0` | `ACCEPT`. |
| `1` | `REJECT` por errores del programa. |
| `2` | Error de archivo, gramática, perfil o configuración. |

En PowerShell puede consultarse inmediatamente con:

```powershell
$LASTEXITCODE
```

## 10. Demostración reproducible para el profesor

### Paso 1: preparar el ambiente

```powershell
python --version
java -version
dot -V
python -m pip install -r requirements.txt
```

Requisitos principales:

- Python 3.10 o superior;
- Java 11 o superior;
- `antlr4-python3-runtime==4.13.2`;
- PyQt6;
- Graphviz disponible en `PATH`.

La primera ejecución puede descargar el JAR oficial de ANTLR. Para una defensa
sin Internet conviene ejecutar previamente una prueba o definir `ANTLR4_JAR`.

### Paso 2: ejecutar la evidencia `.cps`

```powershell
python -m pytest tests/semantic/test_cps_programs.py -q
```

Resultado verificado:

```text
71 passed
```

Esta suite:

- ejecuta todos los `.cps` de la carpeta;
- exige cero diagnósticos en los válidos;
- exige rechazo y una categoría aislada en cada inválido;
- comprueba el warning de código inalcanzable;
- verifica los cuatro tipos de scope;
- verifica las seis categorías de la demostración inválida;
- falla si aparece un `.cps` que no esté registrado.

### Paso 3: demostrar un programa correcto

```powershell
python -m src.main --cps tests/cps/demostracion-valida.cps
```

Debe imprimir una tabla con `BaseCounter`, `Counter`, `isEven`, `isOdd`, campos,
métodos, parámetros y scopes. Al final:

```text
ACCEPT — análisis sintáctico y semántico
```

### Paso 4: demostrar acumulación de errores

```powershell
python -m src.main --cps tests/cps/demostracion-invalida.cps
```

Debe terminar en `REJECT` y mostrar:

- `type`: inicialización incompatible;
- `scope`: identificador ausente;
- `function`: retorno y aridad incorrectos;
- `control_flow`: `break` fuera de bucle;
- `class`: miembro inexistente;
- `array`: lista heterogénea.

El código de salida `1` es el resultado esperado del programa inválido, no un
fallo interno del analizador.

### Paso 5: demostrar warnings

```powershell
python -m src.main --cps `
  tests/cps/advertencias/GEN-01-codigo-inalcanzable.cps
```

Debe aparecer un warning `general` de instrucción inalcanzable, pero el resultado
permanece en `ACCEPT`.

### Paso 6: ejecutar toda la regresión

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest tests -q
```

Resultado verificado en esta entrega:

```text
385 passed
```

### Paso 7: mostrar generalidad

```powershell
python -m pytest tests/antlr_mode/test_runner.py `
  tests/semantic/test_generic_grammar.py -q
```

Estas pruebas procesan Compiscript y MiniCalc con el mismo frontend y el mismo
motor, sin agregar condicionales de lenguaje al runner.

### Paso 8: demostrar la GUI

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest tests/gui/test_cps_workflow.py -q
```

Después repetir manualmente los pasos de la sección 8 con los dos programas
integrales.

## 11. Qué prueba cada suite

| Suite | Evidencia |
|---|---|
| `tests/antlr_mode/` | Inspección de `.g4`, generación, caché, tokens, errores, consumo completo, árbol y segunda gramática. |
| `tests/semantic/test_types.py` | Modelo y compatibilidad de tipos. |
| `tests/semantic/test_expressions.py` | Literales, operadores, asignación, ternarios, listas e índices. |
| `tests/semantic/test_evaluator.py` | Fases de acciones y recorrido genérico. |
| `tests/semantic/test_profile.py` | Esquema JSON, selectores, identidad y fingerprint. |
| `tests/semantic/test_antlr_listener.py` | Eventos del Listener sobre árbol nativo. |
| `tests/semantic/test_generic_grammar.py` | MiniCalc y desacoplamiento de Compiscript. |
| `tests/semantic/test_end_to_end.py` | Matriz semántica mediante fuentes reales. |
| `tests/semantic/test_cps_programs.py` | Los 69 archivos `.cps` presentables. |
| `tests/gui/test_cps_workflow.py` | IDE-01 a IDE-08. |
| `tests/cases/` y pruebas de lexer/parser | Regresión del flujo YALex + YAPar. |

## 12. Mapa rápido del código

| Si preguntan por… | Mostrar… |
|---|---|
| Punto de entrada y opciones CLI | `src/main.py` |
| Gramática final disponible | `src/compiscript/grammar/Compiscript.g4` |
| Descubrimiento de reglas `.g4` | `src/antlr_mode/grammar_info.py` |
| Generación, caché, Lexer, Parser y árbol | `src/antlr_mode/runner.py` |
| Árbol común | `src/parser/parse_tree.py` |
| Perfil real de Compiscript | `semantic_profiles/compiscript.semantic.json` |
| Perfil de prueba genérica | `semantic_profiles/minicalc.semantic.json` |
| Lectura y validación del perfil | `src/semantic/profile.py` |
| Acciones permitidas | `src/semantic/action_registry.py` y `actions/__init__.py` |
| Integración pública | `src/semantic/antlr_adapter.py` |
| Listener de ANTLR | `src/semantic/antlr_listener.py` |
| Estado y recorrido semántico | `src/semantic/evaluator.py` |
| Tipos y compatibilidad | `src/semantic/types.py` |
| Expresiones | `src/semantic/expression_actions.py` |
| Scopes y símbolos | `src/semantic/symbol_table.py` |
| Funciones, control y clases | `src/semantic/actions/` |
| Diagnósticos | `src/semantic/diagnostics.py` |
| Integración visual y workers | `src/gui/app.py` |
| Panel semántico | `src/gui/semantic_results.py` |
| Árbol navegable | `src/gui/parse_tree_view.py` |
| Casos demostrativos | `tests/cps/` |
| Matriz automatizada | `tests/semantic/test_cps_programs.py` |

## 13. Evidencia de requisitos ANTLR e IDE

Los `.cps` prueban el comportamiento del lenguaje, pero algunos requisitos no
pueden demostrarse únicamente con un archivo fuente.

### Integración ANTLR

| ID | Evidencia principal |
|---|---|
| ANT-01 | `runner.py` genera Lexer/Parser y `test_runner.py` ejecuta Compiscript. |
| ANT-02 | `antlr_listener.py` y `test_antlr_listener.py` usan `ParseTreeWalker`. |
| ANT-03 | `parse_tree.py` y pruebas de metadatos conservan árbol y posiciones. |
| ANT-04 | `visualizer.py`, `parse_tree_view.py` y pruebas GUI muestran el árbol. |
| ANT-05 | `test_reports_input_left_after_selected_start_rule` prueba consumo completo. |
| ANT-06 | Gramática, perfil, demos y pruebas end-to-end se ejecutan juntos. |

### Flujo del IDE

[`tests/gui/test_cps_workflow.py`](../../tests/gui/test_cps_workflow.py) cubre:

| ID | Evidencia |
|---|---|
| IDE-01 | Abrir `.cps`. |
| IDE-02 | Editar y analizar el contenido actual. |
| IDE-03 | Guardar y conservar extensión `.cps`. |
| IDE-04 | Compilar sintaxis + semántica. |
| IDE-05 | Mostrar diagnósticos ubicados y categorizados. |
| IDE-06 | Mostrar tabla por entorno. |
| IDE-07 | Mostrar imagen y árbol navegable. |
| IDE-08 | Ejecutar análisis en `QThread`. |

## 14. Limitaciones que deben explicarse honestamente

1. Una `.g4` externa puede analizarse sintácticamente sin modificar Python,
   siempre que sea una gramática combinada soportada por el runner.
2. La semántica no se deduce automáticamente de una gramática; una forma de
   árbol diferente necesita un perfil compatible.
3. El fingerprint rechazará el perfil de Compiscript si la gramática cambia.
   Eso es protección, no falta de flexibilidad: obliga a revisar el mapping.
4. Las gramáticas lexer/parser separadas, imports complejos o modos de lexer no
   están cubiertos por el runner actual.
5. Las funciones globales admiten prepass y recursión mutua; las funciones
   anidadas conservan declaración secuencial y no tienen prepass mutuo propio.
6. El proyecto analiza Compiscript, pero no lo interpreta ni genera ejecutables.
7. Debe confirmarse manualmente que `Compiscript.g4` coincide con la última
   versión oficial proporcionada por el profesor.

Si el profesor entrega solamente un `.cps`, se usa la gramática y el perfil
incluidos. Si entrega una `.g4` nueva, primero se prueba sintaxis; para semántica
completa se debe adaptar o crear el perfil correspondiente.

## 15. Guion sugerido para explicar el proyecto

### Versión de 5–7 minutos

1. **Objetivo:** “Extendimos el IDE original con un modo ANTLR que compila
   archivos Compiscript hasta análisis semántico y tabla de símbolos”.
2. **Separación:** “La `.g4` define sintaxis; el `.semantic.json` relaciona el
   árbol con acciones seguras; el `.cps` es el programa”.
3. **Frontend:** mostrar `grammar_info.py` y `runner.py`; explicar generación y
   caché por hash.
4. **Integración:** mostrar `analyze_semantics_with_g4`; explicar que semántica
   solo corre si sintaxis fue válida.
5. **Motor:** mostrar Listener, evaluador, tabla de símbolos y carpeta de
   acciones.
6. **Generalidad:** mostrar los dos perfiles y explicar MiniCalc.
7. **Demostración:** ejecutar el `.cps` válido y el inválido.
8. **Pruebas:** ejecutar las 71 pruebas `.cps` y enseñar la suite completa.
9. **GUI:** mostrar tokens, árbol, diagnósticos y scopes.
10. **Cierre:** mencionar límites de gramáticas externas y fingerprint.

## 16. Preguntas probables del profesor

### “¿Por qué necesitan un perfil si ya tienen la gramática?”

Porque la gramática solo reconoce estructura. Por ejemplo, sabe que existe
`expresión + expresión`, pero no decide si sumar un boolean es válido, qué tipo
resulta ni qué diagnóstico emitir. Esa decisión vive en las acciones semánticas
enlazadas por el perfil.

### “¿Por qué hay dos perfiles JSON?”

Compiscript usa el perfil completo de la entrega. MiniCalc usa uno pequeño para
probar que Listener, evaluador y acciones funcionan con otra gramática sin
modificar el motor.

### “¿Qué ocurre si cambio la gramática?”

El frontend puede regenerar Lexer y Parser automáticamente. Si solo se requiere
sintaxis, funciona sin perfil. Si se requiere semántica y cambió la forma del
árbol, se actualiza el perfil. El fingerprint impide aplicar silenciosamente un
perfil viejo.

### “¿Usaron Visitor o Listener?”

ANTLR se invoca con `-visitor -no-listener`: genera las clases de Visitor, pero
no un Listener específico de la gramática. El flujo semántico no depende de esas
clases específicas; usa `ParseTreeWalker.DEFAULT.walk` con el Listener genérico
propio `SemanticTreeListener`, que hereda de `antlr4.ParseTreeListener` y recibe
los eventos `enterEveryRule` y `exitEveryRule` del árbol nativo.

### “¿Cómo manejan los ámbitos?”

La tabla forma un árbol de scopes. Cada bloque, función y clase abre un hijo; la
resolución busca primero localmente y luego asciende. Al cerrar un scope se
restaura el padre, pero el scope cerrado se conserva para mostrarlo.

### “¿Cómo soportan recursión y declaraciones adelantadas?”

Antes de recorrer cuerpos, `program.predeclare` registra clases, miembros y
firmas globales. Por eso una llamada puede resolver una función posterior y dos
funciones globales pueden llamarse mutuamente.

### “¿Por qué no se detienen en el primer error?”

Las acciones agregan diagnósticos a un `DiagnosticBag` y devuelven `ERROR`. Ese
tipo se propaga sin crear cascadas innecesarias, permitiendo continuar y mostrar
varios errores en una sola compilación.

### “¿Cómo prueban que la GUI no se congela?”

Los análisis se ejecutan en `AntlrAnalysisWorker` o
`SemanticAnalysisWorker`, ambos `QThread`, fuera del hilo principal de Qt.
IDE-08 verifica automáticamente que el worker semántico sea un `QThread`, que
termine y que entregue un resultado válido. Durante la demostración se confirma
visualmente la capacidad de respuesta de la ventana mientras corre el análisis;
la prueba automatizada no mide latencia de interacción de la interfaz.

### “¿Un warning rechaza el programa?”

No. La aceptación semántica busca diagnósticos con severidad `ERROR`. El código
inalcanzable se reporta como `WARNING` y se conserva `ACCEPT`.

## 17. Lista de control antes de presentar

- [ ] Ejecutar `python -m pytest tests -q`.
- [ ] Verificar Java con `java -version`.
- [ ] Verificar Graphviz con `dot -V`.
- [ ] Ejecutar ANTLR una vez para preparar la caché.
- [ ] Abrir la GUI y cargar gramática, perfil y demo válida.
- [ ] Confirmar `Start = program`.
- [ ] Mostrar tokens y árbol sintáctico.
- [ ] Mostrar tabla de símbolos con cuatro tipos de scope.
- [ ] Repetir con `demostracion-invalida.cps`.
- [ ] Enseñar las seis categorías de error.
- [ ] Ejecutar la suite de 71 pruebas `.cps`.
- [ ] Tener lista la explicación de los dos perfiles JSON.
- [ ] Aclarar que una gramática externa requiere perfil propio para semántica.
- [ ] Confirmar cuál gramática considera oficial el profesor.

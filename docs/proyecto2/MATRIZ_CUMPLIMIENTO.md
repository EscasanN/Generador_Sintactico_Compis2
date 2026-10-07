# Matriz de cumplimiento — Proyecto 2

## Uso de la matriz

Esta es la fuente de verdad para saber si la entrega está lista. Cada ID debe
tener una prueba localizable y, cuando corresponda, un archivo .cps de
demostración.

Estado actual: planificación. Ninguna fila se considera satisfecha hasta que la
ruta de evidencia exista y la prueba pase.

## Trazabilidad de la rúbrica

| Componente | Puntos | Evidencia requerida | Bloque principal |
|---|---:|---|---|
| Diseño de CI | 25 | Catálogo, sintaxis, supuestos, ejemplos y verificador coherentes. | Daniel |
| Generación de TAC | 65 | Lowering completo, temporales, pipeline, fixtures e IDE. | Daniel, Dulce y Nelson |
| Tabla de símbolos | 10 | Direcciones, offsets, tamaños, etiquetas y activaciones. | Nadissa |
| Total | 100 | Programa funcional y documentado el día de evaluación. | Equipo |

## Condición de compilación aceptada

CompilationResult.accepted solo puede ser verdadero si:

1. lexer y parser aceptan toda la entrada;
2. el perfil coincide con la gramática;
3. el análisis semántico no tiene errores;
4. el generador cubre todos los nodos alcanzados;
5. IRVerifier no encuentra errores;
6. existe un IRProgram y texto TAC.

Un warning semántico no bloquea TAC. Un error de cualquier fase sí lo bloquea.

## Diseño de código intermedio

| ID | Requisito | Evidencia positiva | Evidencia negativa | Responsable |
|---|---|---|---|---|
| IR-01 | Cuádruplo estructurado con opcode, operandos y resultado. | Construir todas las formas válidas. | Rechazar opcode o aridad inválidos. | Daniel |
| IR-02 | Operandos distinguen constante, símbolo, temporal, etiqueta y offset. | Cada clase se serializa sin ambigüedad. | Tipo de operando incorrecto produce error. | Daniel |
| IR-03 | Programa separa código global y procedimientos. | Función no se ejecuta por caída del global. | Procedimiento sin cierre se rechaza. | Daniel |
| IR-04 | Formato textual consistente y documentado. | Dos serializaciones son idénticas. | Objeto no soportado no usa repr inestable. | Daniel |
| IR-05 | Instrucciones conservan ubicación fuente. | TAC permite relacionar línea de .cps. | Instrucción derivada sin ubicación falla verificación. | Daniel |
| IR-06 | Verificador comprueba definición, etiquetas y llamadas. | IR válida produce cero diagnósticos. | Uso antes de definir y etiqueta ausente se detectan. | Daniel |

## Expresiones y asignaciones

| ID | Requisito | Caso positivo | Caso negativo o invariante | Responsable |
|---|---|---|---|---|
| EXP-01 | +, -, *, / respetan el árbol de precedencia. | x + y * z emite MUL antes de ADD. | No se reconstruye desde texto plano. | Daniel |
| EXP-02 | Operadores unarios. | -x y !b emiten NEG y NOT. | Operando sin hecho semántico produce IRGEN interno. | Daniel |
| EXP-03 | && y || preservan cortocircuito. | RHS queda detrás de un salto. | No aparecen ambos operandos como cálculo incondicional. | Daniel |
| EXP-04 | ==, !=, <, <=, >, >= producen boolean. | Un caso por comparador. | Opcode/comparador desconocido se rechaza. | Daniel |
| EXP-05 | Declaraciones y asignaciones usan el Symbol resuelto. | Shadowing escribe en offsets distintos. | No se elige símbolo solo por nombre. | Daniel y Nadissa |
| EXP-06 | Constantes no se escriben después de declarar. | Inicialización de const genera una copia. | El error semántico posterior impide TAC. | Dulce |
| EXP-07 | Ternario evalúa una sola rama. | Etiquetas de true, false y unión. | No genera ambas ramas en secuencia incondicional. | Daniel |
| EXP-08 | Asignación a campo o índice usa store especializado. | FIELD_SET y LIST_SET. | No se convierte el destino en una copia ordinaria. | Dulce |

## Control de flujo

| ID | Requisito | Caso positivo | Caso negativo o invariante | Responsable |
|---|---|---|---|---|
| CTL-01 | if sin else. | Condición falsa salta al final. | Destino debe existir. | Dulce |
| CTL-02 | if/else. | Rama true salta sobre else. | Solo una rama se ejecuta. | Dulce |
| CTL-03 | while. | Condición se evalúa antes de cada iteración. | continue no salta al cuerpo directamente. | Dulce |
| CTL-04 | do-while. | Cuerpo aparece antes de condición. | Condición falsa inicial no evita primera vuelta. | Dulce |
| CTL-05 | cuatro formas de for de la gramática. | Init, condición opcional, update opcional y cuerpo. | continue apunta a update. | Dulce |
| CTL-06 | switch con case y default. | Discriminante evaluado una vez y dispatch por etiquetas. | Caso sin destino o evaluación repetida falla. | Dulce |
| CTL-07 | break usa el bucle más cercano. | Bucle anidado sale del interno. | break fuera de bucle no llega a codegen. | Dulce |
| CTL-08 | continue usa destino correcto por tipo de bucle. | while, do y for con destinos diferentes. | continue fuera de bucle no genera TAC. | Dulce |

## Funciones, procedimientos y closures

| ID | Requisito | Caso positivo | Caso negativo o invariante | Responsable |
|---|---|---|---|---|
| FUN-01 | Definición produce procedimiento y etiqueta única. | Dos funciones conservan cuerpos separados. | Etiquetas duplicadas se rechazan. | Dulce y Nadissa |
| FUN-02 | Parámetros se declaran en orden y con offset. | Firma con varios tipos. | Slots solapados se rechazan. | Nadissa |
| FUN-03 | Llamada evalúa y emite argumentos de izquierda a derecha. | PARAM, PARAM, CALL con aridad 2. | Cantidad PARAM/CALL incoherente falla verificación. | Dulce |
| FUN-04 | Retorno void y con valor. | RETURN correcto por firma. | Error de retorno semántico impide TAC. | Dulce |
| FUN-05 | Recursión directa. | Factorial llama a su propia etiqueta. | No se crea etiqueta diferente por llamada. | Dulce |
| FUN-06 | Recursión mutua global. | f llama g declarada después. | Símbolo no predeclarado no se inventa. | Dulce |
| FUN-07 | Función anidada crea closure. | CLOSURE une etiqueta y entorno. | No usa una dirección de frame expirado. | Dulce y Nadissa |
| FUN-08 | Captura usa enlace de acceso y distancia léxica. | Captura a uno y dos niveles. | No se sustituye por control link. | Nadissa |
| FUN-09 | Registro de activación contiene campos obligatorios. | Retorno, links, parámetros, locales y temporales. | Layout incompleto o solapado se rechaza. | Nadissa |

## Clases y objetos

| ID | Requisito | Caso positivo | Caso negativo o invariante | Responsable |
|---|---|---|---|---|
| CLS-01 | Clase tiene layout y etiqueta. | Campos con offsets alineados. | Dos campos no comparten offset. | Nadissa |
| CLS-02 | new reserva objeto y llama constructor. | OBJECT_NEW más CALL con this. | Constructor semánticamente inválido no genera TAC. | Dulce |
| CLS-03 | Acceso a atributo usa offset del Symbol. | FIELD_GET y FIELD_SET. | Miembro inexistente se detiene en semántica. | Dulce |
| CLS-04 | Método recibe this oculto. | Llamada incluye objeto receptor. | this fuera de clase no genera TAC. | Dulce |
| CLS-05 | Constructor implícito sin argumentos. | Clase sin constructor acepta new C(). | Argumentos extra se rechazan antes de TAC. | Dulce |
| CLS-06 | Herencia conserva layout base. | Campos heredados preceden a campos propios. | Offset heredado no se redefine accidentalmente. | Nadissa y Dulce |

## Listas

| ID | Requisito | Caso positivo | Caso negativo o invariante | Responsable |
|---|---|---|---|---|
| LST-01 | Lista vacía y no vacía. | LIST_NEW y stores en orden. | Elementos incompatibles impiden TAC. | Dulce |
| LST-02 | Lectura por índice. | LIST_GET produce temporal del tipo del elemento. | Índice no integer impide TAC. | Dulce |
| LST-03 | Escritura por índice. | LIST_SET conserva lista, índice y valor. | Store incompatible no se emite. | Dulce |
| LST-04 | Foreach de la gramática actual. | LIST_LEN, índice, carga e incremento. | Iterable no lista impide TAC. | Dulce |

## Temporales

| ID | Requisito | Caso positivo | Caso negativo o invariante | Responsable |
|---|---|---|---|---|
| TMP-01 | acquire crea nombres únicos mientras están vivos. | Dos resultados simultáneos usan nombres distintos. | No entrega un temporal activo. | Daniel |
| TMP-02 | release habilita reciclaje. | Secuencia independiente reutiliza t0. | Doble release se rechaza. | Daniel |
| TMP-03 | El resultado sigue vivo hasta consumo. | Padre consume hijos antes de liberar. | Uso después de release falla. | Daniel |
| TMP-04 | Ramas conservan temporales hasta la unión. | Ternario libera después de merge. | No reutiliza un valor vivo de otra rama. | Daniel |
| TMP-05 | Frame reserva el pico, no todos los temporales históricos. | peak_active coincide con slots. | Menos slots que el pico falla layout. | Nadissa |

## Tabla de símbolos y entorno de ejecución

| ID | Requisito | Caso positivo | Caso negativo o invariante | Responsable |
|---|---|---|---|---|
| SYM-01 | Símbolo conserva clase de almacenamiento. | global, parameter, local, field y captured. | Clase desconocida se rechaza. | Nadissa |
| SYM-02 | Cada símbolo tiene tamaño y alineación. | Primitivos y referencias según modelo. | Tamaño cero o desalineado falla. | Nadissa |
| SYM-03 | Dirección u offset es visible. | Shadowing produce slots diferentes. | Solapamiento se detecta. | Nadissa |
| SYM-04 | Función, método y clase tienen etiqueta. | Etiquetas deterministas y únicas. | Duplicado falla. | Nadissa |
| SYM-05 | Nivel léxico y captura quedan registrados. | Closure muestra distancia de acceso. | Captura inexistente no se inventa. | Nadissa |
| SYM-06 | La misma declaración semántica alimenta layout y codegen. | Symbol conserva identidad entre fases y aparece en la vista final. | No se crea una tabla paralela basada solo en nombres. | Nadissa y Dulce |
| RUN-01 | Frame incluye parámetros y locales. | Layout estable por función. | Scope de otra función no contamina. | Nadissa |
| RUN-02 | Frame incluye valor y dirección de retorno. | Header completo. | Campo obligatorio ausente falla. | Nadissa |
| RUN-03 | Frame diferencia control y access link. | Función anidada muestra ambos. | Caller no sustituye entorno léxico. | Nadissa |
| RUN-04 | Frame incluye slots temporales. | Reserva peak_active alineado. | Slot menor o solapado falla. | Nadissa |

## Pipeline y salidas

| ID | Requisito | Evidencia | Responsable |
|---|---|---|---|
| PIPE-01 | Sintaxis inválida detiene semántica y TAC. | .cps con error sintáctico; intermediate_result ausente. | Dulce |
| PIPE-02 | Semántica inválida detiene TAC. | .cps con tipos inválidos; intermediate_result ausente. | Dulce |
| PIPE-03 | Warning permite TAC. | Programa con código inalcanzable según política acordada. | Dulce |
| PIPE-04 | Codegen inválido rechaza compilación. | IRGEN-UNSUPPORTED o verifier error. | Dulce |
| PIPE-05 | Programa válido entrega TAC, layouts y estadísticas. | DEMO completa desde Python. | Dulce |
| OUT-01 | CLI imprime TAC. | Opción --emit-tac sin ruta. | Nelson |
| OUT-02 | CLI guarda TAC. | Archivo UTF-8 solicitado explícitamente. | Nelson |
| OUT-03 | IDE muestra TAC. | Pestaña legible y actualizada. | Nelson |
| OUT-04 | IDE muestra tabla extendida y frames. | Vista navegable. | Nelson |
| OUT-05 | IDE muestra errores con tipo y ubicación. | Error léxico, sintáctico, semántico e IR. | Nelson |
| IDE-01 | Crear, abrir, editar, guardar y compilar .cps. | Flujo manual completo. | Nelson |
| IDE-02 | Trabajo pesado fuera del hilo Qt. | Prueba del worker y botón deshabilitado. | Nelson |
| IDE-03 | Error limpia TAC anterior. | Compilar válido y luego inválido. | Nelson |

## Batería y entrega

| ID | Requisito | Evidencia | Responsable |
|---|---|---|---|
| TST-01 | Caso .cps positivo por dominio. | tests/cps/codegen/validos. | Nelson |
| TST-02 | Caso fallido por fase. | tests/cps/codegen/invalidos y tests/codegen. | Nelson |
| TST-03 | Golden TAC representativo. | tests/cps/codegen/esperados. | Nelson |
| TST-04 | Regresión de fase anterior. | tests/semantic y tests/antlr_mode verdes. | Equipo |
| TST-05 | Suite completa desde clon limpio. | Comando y resultado documentados. | Nelson |
| DOC-01 | Arquitectura coincide con código real. | ARQUITECTURA.md actualizado. | Nelson |
| DOC-02 | Lenguaje TAC tiene ejemplos y supuestos. | DISENO_TAC.md actualizado. | Daniel y Nelson |
| DOC-03 | README explica instalación y ejecución. | README principal. | Nelson |
| GIT-01 | Commits individuales. | Historial por los cuatro integrantes. | Equipo |

## Cobertura adicional de la gramática vigente

El enunciado mínimo no enumera todo lo que ya acepta Compiscript. Estas filas
evitan un ACCEPT semántico seguido de código incompleto.

| ID | Construcción | Resultado esperado | Responsable |
|---|---|---|---|
| EXT-01 | print | CALL al runtime abstracto de impresión. | Dulce |
| EXT-02 | módulo | MOD. | Daniel |
| EXT-03 | ternario | control por etiquetas y merge. | Daniel |
| EXT-04 | foreach | lowering indexado de lista. | Dulce |
| EXT-05 | herencia | layout base y resolución de método documentada. | Nadissa y Dulce |
| EXT-06 | null | operando inmediato tipado. | Daniel |
| EXT-07 | try/catch | instrucciones de alto nivel o diagnóstico acordado. | Dulce |
| EXT-08 | alternativa alcanzada sin handler | error IR explícito; nunca TAC parcial aceptado. | Dulce |

## Comandos esperados

~~~powershell
python -m pytest tests/codegen -q
python -m pytest tests/semantic -q
python -m pytest tests/antlr_mode -q
python -m pytest tests/gui -q
python -m pytest tests -q
python -m src.main --cps tests/cps/codegen/validos/DEMO-completa.cps --emit-tac
~~~

## Cierre

El proyecto no está listo solo porque produce texto parecido a TAC. Debe
cumplirse todo lo siguiente:

- cada ID obligatorio tiene evidencia;
- toda salida está estructurada y verificada;
- los temporales se reciclan sin violar vida;
- las funciones anidadas usan entorno léxico;
- la tabla extendida y frames son visibles;
- IDE y CLI recorren el mismo pipeline;
- una entrada inválida no produce ni conserva TAC;
- la documentación coincide con el comportamiento;
- el historial identifica las contribuciones individuales.

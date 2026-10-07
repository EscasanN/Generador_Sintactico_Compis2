# Diseño propuesto del lenguaje intermedio TAC

## Propósito y estado

Este documento fija el contrato inicial del código intermedio para que los
cuatro bloques trabajen sobre la misma representación. Es una decisión de
diseño propuesta; al implementar el bloque 1 debe convertirse en la
especificación ejecutable y mantenerse sincronizada con las pruebas.

El diseño prioriza:

- instrucciones simples y tipadas;
- lectura clara durante la presentación;
- verificación automática;
- temporales reciclables;
- control de flujo explícito;
- soporte visible para funciones, closures, objetos y listas;
- independencia de una arquitectura real.

## Representación canónica

La fuente de verdad es un cuádruplo estructurado:

~~~text
(opcode, arg1, arg2, result)
~~~

Cada instrucción también conserva tipo de resultado y ubicación fuente. Los
campos no usados contienen ausencia, nunca una cadena ambigua.

Un operando tiene una clase explícita:

| Clase | Ejemplo | Significado |
|---|---|---|
| constante | 4, 3.5, true, "hola", null | valor inmediato |
| símbolo | global@x, frame@-8 | ubicación asignada a una declaración |
| temporal | t0, t1 | resultado intermedio reciclable |
| etiqueta | L0, fn_suma | destino de control o procedimiento |
| offset | 16 | desplazamiento en bytes |

El texto TAC es una serialización para humanos. Las pruebas de invariantes usan
los objetos estructurados.

## Organización del programa

~~~text
program
    global:
        instrucciones de inicialización global

    procedure fn_nombre(param0, param1):
        instrucciones
        return
~~~

Las funciones no se insertan dentro del flujo global mediante saltos
artificiales. Cada función o método tiene una sección de procedimiento. Una
función anidada también tiene etiqueta propia; al ejecutar su declaración se
construye una closure que une esa etiqueta con el entorno de definición.

## Catálogo mínimo de instrucciones

### Datos y expresiones

| Forma textual | Cuádruplo conceptual | Uso |
|---|---|---|
| x = y | COPY, y, –, x | copia o asignación |
| t = x op y | ADD/SUB/MUL/DIV/MOD/CMP, x, y, t | operación binaria |
| t = op x | NEG/NOT, x, –, t | operación unaria |
| t = cast T x | CAST, x, T, t | conversión explícita si se requiere |

Los comparadores son EQ, NE, LT, LE, GT y GE. Producen boolean.

### Control de flujo

| Forma textual | Cuádruplo conceptual | Uso |
|---|---|---|
| L: | LABEL, –, –, L | define una etiqueta |
| goto L | GOTO, –, –, L | salto incondicional |
| if x goto L | IF_TRUE, x, –, L | salto si verdadero |
| ifFalse x goto L | IF_FALSE, x, –, L | salto si falso |

### Procedimientos

| Forma textual | Cuádruplo conceptual | Uso |
|---|---|---|
| param x | PARAM, x, –, – | argumento explícito |
| t = call f, n | CALL, f, n, t | llamada con retorno |
| call f, n | CALL, f, n, – | llamada sin retorno |
| return x | RETURN, x, –, – | retorno con valor |
| return | RETURN, –, –, – | retorno void |

Los argumentos se evalúan de izquierda a derecha. Para métodos, closures y
constructores pueden existir parámetros ocultos documentados: this y env.

### Listas

| Forma textual | Cuádruplo conceptual | Uso |
|---|---|---|
| t = list_new n | LIST_NEW, n, –, t | reserva una lista |
| list_set a, i, x | LIST_SET, a, i, x | almacena un elemento |
| t = list_get a, i | LIST_GET, a, i, t | carga un elemento |
| t = list_len a | LIST_LEN, a, –, t | obtiene longitud |

El índice de esta IR es lógico. La escala por tamaño del elemento se conserva en
el layout y se materializará en un backend posterior. No se debe multiplicar el
índice dos veces.

### Objetos y miembros

| Forma textual | Cuádruplo conceptual | Uso |
|---|---|---|
| t = object_new C, size | OBJECT_NEW, C, size, t | reserva una instancia |
| field_set o, offset, x | FIELD_SET, o, offset, x | escribe un campo |
| t = field_get o, offset | FIELD_GET, o, offset, t | lee un campo |
| t = method_ref o, label | METHOD_REF, o, label, t | prepara método ligado |

La creación de un objeto se traduce como reserva, paso implícito de this y
llamada al constructor resuelto.

### Closures y acceso no local

| Forma textual | Cuádruplo conceptual | Uso |
|---|---|---|
| t = env_new n | ENV_NEW, n, –, t | crea entorno capturado |
| env_set e, offset, x | ENV_SET, e, offset, x | guarda una captura |
| t = env_get e, depth, offset | ENV_GET, e, depth:offset, t | lee no local |
| t = closure f, e | CLOSURE, f, e, t | une código y entorno |
| t = closure_call c, n | CLOSURE_CALL, c, n, t | invoca con env oculto |

El enlace de acceso no se confunde con el enlace de control. El primero sigue
anidamiento léxico; el segundo identifica al caller dinámico.

### Excepciones de la gramática actual

El mínimo oficial no exige try/catch, pero Compiscript ya lo acepta. Para no
generar código incorrecto silenciosamente se reserva:

| Forma textual | Uso |
|---|---|
| try_begin Lcatch | instala manejador |
| try_end | retira manejador |
| catch x | enlaza la excepción capturada |

Estas operaciones son IR de alto nivel. Su implementación de runtime queda
fuera de este proyecto.

## Reglas de traducción

### Precedencia y asociatividad

El parser ya resolvió la estructura de la expresión. El generador recorre el
árbol en postorden, por lo que no vuelve a interpretar texto ni precedencia.

Fuente:

~~~text
x + y * z
~~~

TAC:

~~~text
t0 = y * z
t1 = x + t0
~~~

### Asignación

~~~text
let r: integer = a + b;
~~~

~~~text
t0 = a + b
r = t0
~~~

La ubicación r proviene del layout del símbolo; el nombre se muestra en la
serialización para facilitar la defensa.

### Cortocircuito lógico

No es válido calcular ambos operandos incondicionalmente. Para a && b:

~~~text
t0 = false
ifFalse a goto Lend
ifFalse b goto Lend
t0 = true
Lend:
~~~

Para a || b:

~~~text
t0 = true
if a goto Lend
if b goto Lend
t0 = false
Lend:
~~~

Esto preserva efectos laterales y excepciones del segundo operando.

### Condicional

~~~text
if (c) { S1 } else { S2 }
~~~

~~~text
ifFalse c goto Lelse
S1
goto Lend
Lelse:
S2
Lend:
~~~

### While

~~~text
Lcond:
ifFalse c goto Lexit
cuerpo
goto Lcond
Lexit:
~~~

continue apunta a Lcond y break apunta a Lexit.

### Do-while

~~~text
Lbody:
cuerpo
Lcond:
if c goto Lbody
Lexit:
~~~

continue apunta a Lcond para que la condición sí se evalúe.

### For

~~~text
inicialización
Lcond:
ifFalse condición goto Lexit
cuerpo
Lupdate:
actualización
goto Lcond
Lexit:
~~~

Si falta la condición se trata como true. continue apunta a Lupdate.

### Switch

La expresión discriminante se evalúa exactamente una vez:

~~~text
t0 = discriminante
if t0 == caso1 goto Lcase1
if t0 == caso2 goto Lcase2
goto Ldefault
Lcase1:
sentencias1
Lcase2:
sentencias2
Ldefault:
sentenciasDefault
Lend:
~~~

La propuesta conserva caída entre casos. La política de break dentro de switch
debe confirmarse con el profesor; mientras tanto se mantiene la regla semántica
actual: break y continue pertenecen a bucles.

### Llamadas y retorno

~~~text
let r = suma(a, b);
~~~

~~~text
param a
param b
t0 = call fn_suma, 2
r = t0
~~~

La recursión no necesita una instrucción especial: las funciones se
predeclaran, por lo que su etiqueta existe antes de generar el cuerpo.

### Función anidada y closure

Una función anidada recibe un parámetro oculto env. Si captura x:

~~~text
e0 = env_new 1
env_set e0, 0, x
c0 = closure fn_interna, e0
~~~

Dentro de la función:

~~~text
t0 = env_get env, 0, 0
~~~

Si la captura puede sobrevivir al frame creador, el entorno es un objeto de
heap abstracto. El proyecto modela esa decisión; no implementa un recolector.

### Objeto y constructor

~~~text
let p = new Punto(2, 3);
~~~

~~~text
t0 = object_new Punto, 16
param t0
param 2
param 3
call Punto.constructor, 3
p = t0
~~~

this es el primer parámetro oculto de métodos y constructores. Los campos
heredados, si se cubre la extensión, ocupan primero sus offsets de clase base.

### Lista

~~~text
let a = [10, 20];
let x = a[1];
~~~

~~~text
t0 = list_new 2
list_set t0, 0, 10
list_set t0, 1, 20
a = t0
t1 = list_get a, 1
x = t1
~~~

## Temporales y reciclaje

TemporaryPool mantiene dos conjuntos:

- activos: nombres cuyo valor todavía puede usarse;
- libres: nombres que pueden asignarse de nuevo.

Reglas:

1. acquire devuelve primero un temporal libre compatible; si no hay, crea uno.
2. release solo acepta un temporal activo.
3. un temporal se libera después de su último consumo, nunca al emitir su
   definición.
4. símbolos, constantes y etiquetas no entran al pool.
5. un temporal que atraviesa una rama se libera después del punto de unión.
6. el resultado entregado al caller sigue activo hasta que este lo consume.
7. el verificador rechaza doble liberación, uso después de liberar y dos valores
   vivos con el mismo nombre.

Ejemplo:

~~~text
t0 = a + b
x = t0          # después de COPY, t0 queda libre
t0 = c * d      # reutilización válida
y = t0
~~~

Las pruebas deben demostrar que una expresión secuencial reutiliza nombres y
que una expresión anidada conserva simultáneamente todos los temporales todavía
vivos.

## Modelo abstracto de tamaños y offsets

Mientras no exista una máquina destino oficial se adopta un modelo de 64 bits:

| Tipo | Tamaño | Alineación |
|---|---:|---:|
| boolean | 1 byte | 1 |
| integer | 4 bytes | 4 |
| float | 8 bytes | 8 |
| string | 8 bytes | 8 |
| lista | 8 bytes | 8 |
| clase/objeto | 8 bytes | 8 |
| función/closure | 8 bytes | 8 |
| desconocido o referencia genérica | 8 bytes | 8 |

El offset se alinea antes de asignar cada símbolo. Este layout es un contrato de
la IR, no un ABI real.

Un registro de activación contiene, en orden lógico:

1. dirección o etiqueta de retorno;
2. enlace de control;
3. enlace de acceso;
4. área de valor de retorno;
5. parámetro oculto this o env cuando corresponda;
6. parámetros declarados;
7. variables locales;
8. slots del máximo de temporales vivos.

La tabla extendida registra por símbolo:

- clase de almacenamiento: static, parameter, local, field o captured;
- tamaño y alineación;
- offset o dirección abstracta;
- etiqueta para funciones, métodos y clases;
- nivel léxico;
- distancia de acceso si es no local.

## Verificación obligatoria

Antes de exponer TAC, el verificador comprueba:

- opcode conocido y aridad correcta;
- tipos de operandos compatibles con la instrucción;
- temporal definido antes de cada uso;
- ninguna lectura después de liberar un temporal;
- etiqueta definida exactamente una vez;
- todo salto apunta a una etiqueta definida en el mismo procedimiento;
- cada procedimiento termina con retorno o transferencia definitiva;
- cantidad declarada de argumentos coherente con PARAM;
- offsets alineados y sin solapamiento;
- funciones anidadas con enlace de acceso o entorno explícito;
- ubicación fuente presente en instrucciones derivadas del programa.

Los errores del verificador son fallos de compilación con categoría IR, no
errores semánticos del usuario.

## Delimitación frente a optimización

No se comparten subexpresiones mediante GDA en esta entrega. Dos expresiones
textualmente iguales pueden estar separadas por una escritura, una llamada o
un acceso a memoria. Sin SSA o análisis de alias, reutilizarlas podría cambiar
el programa.

El reciclaje de temporales sí es obligatorio y no elimina cálculos: reutiliza el
nombre o slot únicamente después de que el valor anterior ya no está vivo.

# Diseño de máquina MIPS y convención de ejecución

## Estado y referencias

Contrato de diseño para implementar; no describe un backend existente.
MARS 4.5 es el único destino de aceptación. Se permite ensamblador extendido
y se usan `nop` en delay slots; las pruebas activan delayed branching.
No se promete ABI o ejecutable de Linux ni compatibilidad con hardware real.

- [Opciones oficiales de MARS](https://dpetersanderson.github.io/Help/MarsHelpCommand.html).
- [Syscalls oficiales de MARS](https://dpetersanderson.github.io/Help/SyscallHelp.html).
- [Modelo abstracto del TAC](../proyecto2/DISENO_TAC.md).

## Valores y almacenamiento

| Valor | Representación MIPS | Tamaño de acceso |
|---|---|---:|
| `integer` | Entero con signo de 32 bits, complemento a dos | 4 bytes |
| `boolean` | 0 o 1, sin signo | 1 byte en símbolos/campos; 4 en slots ABI |
| `float` | IEEE 754 doble, par de registros flotantes | 8 bytes |
| `string`, lista, objeto, closure | Dirección MIPS32; cero es `null` | 4 bytes |
| Región abstracta de referencia | Ocho bytes reservados; puntero en los primeros cuatro | 4 bytes y padding |
| Slot ABI/temporal | Ocho bytes alineados; valor escalar en su parte inicial | Según tipo |

Las referencias no se cargan con instrucciones de 64 bits. Reservar ocho bytes
no las convierte en punteros de 64 bits. El padding se inicializa a cero y no
se usa para comparar valores. Booleanos se cargan con `lbu`; enteros y
referencias con `lw`; dobles con `l.d`. Stores correspondientes: `sb`, `sw`, `s.d`.
En slots ABI el booleano se transporta como palabra normalizada.

Se preservan offsets y tamaños de campos y entornos del IR con padding explícito;
los frames reciben un mapa físico propio para parámetros, guardados y spills.
Nunca se cambia un offset aislado sin cambiar su descriptor. Los operandos
`OBJECT_NEW` y `ENV_NEW` expresan bytes; `LIST_NEW` expresa cantidad de elementos.

Memoria de objetos y listas se inicializa a cero. No se agrega análisis de
asignación definida al frontend. Leer un slot no inicializado observa cero,
falso o referencia nula según el tipo. Una cadena nula no equivale a `""`.

### Reglas numéricas

- Literales enteros fuera del rango de 32 bits se rechazan con ubicación fuente; el chequeo se aplica al valor IR efectivamente generado.
- Suma, resta, multiplicación y negación enteras conservan los 32 bits bajos; no generan excepción de overflow.
- División entera trunca hacia cero; módulo es `a - trunc(a/b) * b`.
- `INT_MIN / -1` devuelve `INT_MIN`; su módulo devuelve cero mediante tratamiento explícito.
- División o módulo por cero, también flotante, produce error runtime comprobado.
- Operaciones flotantes usan doble precisión; módulo flotante usa resto con cociente truncado hacia cero calculado en doble, sin limitarlo a un registro entero de 32 bits.
- Conversiones siguen los `CAST` del IR; no se introducen coerciones nuevas entre cadenas y números.
- Comparaciones flotantes respetan IEEE 754: igualdad con NaN es falsa y desigualdad verdadera; no confundir el resultado de comparación con un entero flotante.

Las pruebas incluyen negativos, valores límite y números fraccionarios;
comparación numérica de dobles: `rel_tol=1e-9`, `abs_tol=1e-9`, con casos
separados para infinitos y NaN. No usar tolerancia para esconder errores enteros.

## ABI propia del compilador

Todos los procedimientos usan la misma ABI, incluidos auxiliares del runtime.
Los argumentos se preparan en orden IR en un área contigua de slots de ocho
bytes; los parámetros ocultos se colocan antes que los declarados.

Sea `S` el `$sp` antes de reservar argumentos, `A = 8 * n` su tamaño y `F`
el tamaño del frame, redondeado a ocho bytes:

```text
caller:  sp = S - A; argumento i en sp + 8*i; jal destino; nop
callee:  sp = sp - F; guardar ra/fp; fp = sp
         argumento i se lee en fp + F + 8*i
retorno: cargar resultado; restaurar ra/fp; sp = sp + F; jr ra; nop
caller:  sp = sp + A
```

El descriptor del frame reserva los primeros 32 bytes en slots de ocho:
retorno (`ra`, offset 0), enlace de control (`fp` anterior, 8), enlace de acceso
(16) y respaldo de valor retornado (24). Después se ubican guardados, locales,
temporales y spills alineados. Los parámetros se describen en el área entrante,
sin fingir que sus antiguos offsets abstractos ya son físicos.

El prólogo guarda el `$fp` anterior antes de sustituirlo. El epílogo recupera
`$ra` y el `$fp` anterior usando la base actual antes de liberar `F`. El frame
global usa la misma disciplina de slots pero termina con syscall de salida.
El punto de entrada normaliza la alineación inicial del stack a ocho bytes.

Enteros, booleanos y referencias retornan en `$v0`; dobles en `$f0/$f1`.
El respaldo de retorno del frame se escribe antes de ir al epílogo; `void`
no inventa un valor. `$sp` debe recuperar exactamente `S` tras una llamada.

`CALL` ya cuenta sus argumentos ocultos explícitos. `CLOSURE_CALL` cuenta
solo los `PARAM` que aparecen en IR: su descriptor incorpora `this`/`env`
para construir la firma física. No duplicar parámetros ocultos ni comparar
la aridad fuente con la aridad física sin descontarlos.

Los `PARAM` se capturan como valores en slots de staging; no como referencias
Python que se reevaluarán al llamar. El emisor consume el paquete en la
instrucción de llamada correspondiente. Rechaza paquetes incompletos o aridad
incoherente; preserva valores frente a helpers y evaluación con efectos.

## Asignación de registros

### Bancos y registros reservados

- `$t0` a `$t7`: registros asignables para enteros/referencias.
- `$t8`, `$t9`: auxiliares del emisor; no alojan valores persistentes.
- `$f2/$f3`, `$f4/$f5`, `$f6/$f7`, `$f8/$f9`, `$f10/$f11`: banco asignable de dobles.
- `$f0/$f1`: retorno; `$f12/$f13`: syscalls; `$f14/$f15`, `$f16/$f17`: auxiliares.
- `$s0` a `$s7`: preservados por callee; inicialmente no asignables. No usarlos como scratch.
- `$a0`–`$a3`, `$v0/$v1`, `$ra`, `$sp`, `$fp`, `$at`, `$gp`, `$k0/$k1`: reservados según su función; `$at` pertenece al ensamblador.

### Algoritmo `getReg(value, mode, pinned)`

1. Seleccionar banco por tipo/rol; devolver registro vigente si ya contiene el valor.
2. Preferir registro libre; de no haberlo, elegir víctima no fijada en orden estable.
3. Si la víctima está modificada y viva, almacenarla en su respaldo antes de reutilizarla.
4. Cargar el operando para lectura; para escritura reservar y marcar modificado tras emitir.
5. No expulsar operandos fijados de la instrucción actual; si no hay víctima, usar secuencia de memoria con auxiliares reservados.

Cada valor tiene respaldo en memoria. La clave temporal incluye procedimiento
y préstamo (`lease`), no solo nombre. El plan de slots puede reutilizar una
región cuando las vidas no se superponen; no presupone que el número de nombre
`tN` sea menor que el pico de temporales vivos.

Guardar modificados e invalidar descriptores antes de saltos, uniones y llamadas,
incluidas las que se introducen para concatenar, reservar memoria o fallar.
En entrada de bloque no asumir valores en registros. `RELEASE` libera el préstamo
y no necesita instrucción de CPU. Los helpers respetan la misma ABI; cualquier
uso futuro de `$s` exige guardarlo/restaurarlo y probarlo.

## Heap y datos compuestos

`alloc_aligned(n)` solicita espacio con syscall 9 más padding necesario,
devuelve base alineada a ocho bytes y limpia la región. No libera objetos.
Las pruebas tienen tamaño acotado; agotamiento de memoria no equivale a éxito.

| Estructura | Contrato |
|---|---|
| Lista | Longitud en los primeros 4 bytes, padding hasta offset 8, elementos desde 8 con stride 8. |
| Objeto | Región del tamaño de `ClassLayout`; campos y slots de entornos en sus offsets abstractos preservados. |
| Entorno | Slots y `parent_offset` de `EnvironmentLayout`; los enlaces se siguen con el descriptor de cada ancestro, no con un offset universal supuesto. |
| Callable | Descriptor de 32 bytes: código en 0, entorno en 8, receptor en 16 y máscara de ocultos en 24; slots de ocho, datos de cuatro y padding. |
| Cadena | Longitud en bytes UTF-8 en offset 0, padding hasta 8 y contenido desde offset 8. Longitud explícita permite también bytes nulos en contenido. |

La máscara del descriptor se consulta en runtime: bit 0 indica `env` y bit 1
indica `this`; solo son válidos los bits 0 y 1. `CLOSURE_CALL` inserta primero
`this` si el bit 1 está activo y después `env` si el bit 0 está activo, antes
de los argumentos explícitos. La aridad física es `n + cantidad de bits activos`.
Una función global tiene máscara 0, una closure que recibe entorno tiene 1,
un método sin entorno tiene 2 y un método con entorno tiene 3. No inferir esos
bits de si un puntero es cero. El creador del descriptor obtiene la máscara de
los parámetros ocultos de su `IRProcedure`; la firma fuente sigue validada
semánticamente. Una misma variable de función puede cambiar entre estas formas
sin que su `FunctionType` revele los ocultos. No basta metadata solo estática
en el sitio de llamada. Rechazar descriptores nulos y máscaras inválidas.
`METHOD_REF` lee el entorno del offset indicado por `bound_environment_offset`
en la instancia; no usa el entorno activo del llamador.

Las cadenas literales se emiten como bytes numéricos, evitando escapes
dependientes del ensamblador. Se imprimen mediante syscall 15, descriptor 1,
puntero al contenido y longitud explícita. El adaptador arranca Java con
`-Dfile.encoding=UTF-8` y decodifica UTF-8. La salida Unicode se valida también
en MARS gráfico con esa configuración. Syscall 11 solo cubre el byte bajo y
no sirve para imprimir arbitrariamente caracteres Unicode. Concatenación reserva
espacio nuevo; igualdad recorre contenido, con `null == null` verdadero.
Listas/objetos/callables se comparan por identidad. Orden de cadenas: lexicográfico
por bytes UTF-8 sin signo si la semántica admite la comparación.

`print` es la única etiqueta externa del TAC actual autorizada como entrada de
runtime. Imprime escalares con su servicio correspondiente y agrega un salto
de línea por llamada: booleanos `true`/`false`, nulo `null`, cadenas por contenido.
Referencias compuestas imprimen marcadores estables `[list]`, `[object]`,
`[function]`, sin direcciones variables. Una referencia escalar nula imprime
`null` antes de intentar imprimir su contenido. Esta política es decisión del
equipo y debe mostrarse en los ejemplos de defensa.

## Errores del lenguaje y excepciones

El runtime comprueba `DIV_ZERO`, `INDEX_OUT_OF_RANGE` y `NULL_ACCESS` antes
de ejecutar la operación peligrosa. Un índice negativo también es inválido.
El error transporta una cadena con su código; `CATCH` la almacena en el símbolo
correspondiente. No se agrega sintaxis `throw` a la gramática.

`TRY_BEGIN` instala un registro de 40 bytes alineado con enlace al anterior,
destino catch, `$sp` de restauración, `$fp` y `$ra` de la activación protegida.
La cabeza se guarda en una variable global del runtime, no en un `$s` oculto.
El registro se ubica en stack y su enlace no sobrevive al ámbito protegido.
`TRY_END` lo retira exactamente una vez y restaura su reserva de stack.

Antes de instalar o abandonar el ámbito se guardan valores modificados. Al
fallar, se toma el manejador activo, se restablecen stack/frame/retorno,
se retira ese manejador, se deja el payload en un slot global reservado y se
salta a catch. Los cachés de registros del catch están vacíos. La restauración
descarta las activaciones y los argumentos de llamadas que se abandonan.
Sin manejador, imprimir `RuntimeError: CODIGO` y terminar con código 1 usando
syscall 17. El payload no depende de un temporal de un frame descartado.

Los `TRY_END` que el TAC ya emite antes de `return`, `break` o `continue`
se respetan. No retirar además el mismo manejador en el epílogo. Los errores
de sintaxis, tipos y backend no son excepciones capturables del programa.

## Catálogo exhaustivo del IR actual

| Opcodes | Traducción o auxiliar | Propietario | Matriz |
|---|---|---|---|
| `COPY` | Carga/store según tipo; preservar identidad del símbolo. | Daniel | MEM-01 |
| `ADD`, `SUB`, `MUL`, `DIV`, `MOD` | Entero o doble; `ADD` de cadenas delega al runtime. | Daniel / Dulce para cadenas | NUM-01, STR-01 |
| `EQ`, `NE`, `LT`, `LE`, `GT`, `GE` | Comparación tipada; cadenas delegan al runtime. | Daniel / Dulce para cadenas | NUM-01, STR-01 |
| `NEG`, `NOT`, `CAST` | Negación, normalización booleana y conversión IR. | Daniel | NUM-01 |
| `LABEL`, `GOTO`, `IF_TRUE`, `IF_FALSE` | Etiquetas y branches con barreras. | Daniel | FLOW-01 |
| `RELEASE` | Actualización de vida; sin instrucción obligatoria. | Daniel | REG-03 |
| `PARAM`, `CALL`, `CLOSURE_CALL`, `RETURN` | ABI y paquete de argumentos. `CALL print` despacha por tipo. | Nadissa; impresión base Daniel, compuesta Dulce | CALL-01, CALL-02 |
| `ENV_NEW`, `ENV_SET`, `ENV_GET`, `CLOSURE`, `METHOD_REF` | Entornos y descriptors de callables. | Nadissa | ENV-01, ENV-02, METHOD-01 |
| `LIST_NEW`, `LIST_SET`, `LIST_GET`, `LIST_LEN` | Header, stride, comprobaciones y accesos tipados. | Dulce | LIST-01 |
| `OBJECT_NEW`, `FIELD_SET`, `FIELD_GET` | Reserva de instancia, offsets y acceso nulo. | Dulce | OBJ-01, OBJ-02 |
| `TRY_BEGIN`, `TRY_END`, `CATCH` | Cadena de manejadores y payload. | Dulce | EXC-01, EXC-02, EXC-03 |

En bloque 1, división por cero invoca una interfaz de error cuya implementación
base termina con diagnóstico. Bloque 3 registra el proveedor con manejadores;
la operación escalar no cambia. Igual mecanismo conecta los handlers de cadena.
Ningún opcode desconocido se trata como `nop`; la cobertura compara este catálogo
y el registro de handlers contra el enum real del repositorio.

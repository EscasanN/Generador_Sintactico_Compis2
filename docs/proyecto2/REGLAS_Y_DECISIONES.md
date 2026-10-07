# Reglas, supuestos y decisiones — Proyecto 2

## Cómo usar este documento

Aquí se separan tres categorías:

- **confirmado:** aparece en el enunciado o en la base ya aceptada;
- **decisión de diseño:** propuesta interna del equipo;
- **pendiente:** requiere confirmación del profesor o evidencia adicional.

No se debe convertir una pregunta pendiente en comportamiento definitivo sin
registrar la respuesta y la fecha.

## Requisitos confirmados por el enunciado

| Tema | Regla confirmada |
|---|---|
| Entrada | Archivo fuente Compiscript con extensión .cps. |
| Frontend | ANTLR construye el árbol sintáctico. |
| Orden | La semántica se ejecuta antes de generar código intermedio. |
| Condición | Si existen errores, se reportan en lugar de producir una salida aceptada. |
| Salida | TAC, errores de compilación y estado extendido de la tabla de símbolos. |
| IR | Debe incluir asignación, operaciones, copia, saltos, etiquetas, llamadas y acceso indexado, entre otras. |
| Expresiones | Aritmética, lógica, comparación, declaraciones y asignaciones. |
| Control | if/else, while, do-while, for, switch, break y continue. |
| Funciones | Definición, parámetros, llamadas, retorno y recursión. |
| Closures | Funciones anidadas con acceso al entorno de definición. |
| Clases | Objetos, constructor, atributos, métodos y this. |
| Listas | Creación y acceso indexado. |
| Temporales | Asignación y reciclaje después del consumo. |
| Símbolos | Direcciones o desplazamientos, tamaños y etiquetas. |
| Activaciones | Parámetros, locales, temporales, retorno, control y acceso. |
| IDE | Escribir y compilar Compiscript. |
| Pruebas | Casos exitosos y fallidos, funcionales durante la evaluación. |
| Git | Commits individuales que evidencien la contribución. |

## Base confirmada del repositorio

- El único flujo vigente es Compiscript con ANTLR.
- Compiscript.g4 es la gramática de trabajo del repositorio.
- compiscript.semantic.json está unido a esa gramática por fingerprint.
- analyze_semantics_with_g4 ya entrega árbol, diagnósticos y tabla de símbolos.
- Los warnings no convierten un resultado semántico en REJECT.
- SymbolTable conserva scopes cerrados.
- SemanticValue conoce el Symbol resuelto cuando aplica.
- La GUI ya usa un worker para no bloquear Qt.
- La versión semántica presentada permanece en entrega-semantica-100.

## Decisiones de diseño adoptadas para planificar

| Tema | Decisión | Motivo |
|---|---|---|
| Representación interna | Cuádruplos tipados. | Resultado explícito, fácil verificación y referencias estables. |
| Presentación | TAC textual derivado de los cuádruplos. | Legible para el profesor sin perder estructura. |
| Nueva API | compile_compiscript envuelve la API semántica. | Conserva compatibilidad y separa responsabilidades. |
| Árbol de entrada | ParseTreeNode con anotaciones semánticas. | Ya existe y preserva alternativas y ubicación. |
| Asociación de nombres | Usar Symbol por identidad, no búsqueda textual. | Evita errores con shadowing. |
| Orden de evaluación | Izquierda a derecha. | Convención única y predecible. |
| Lógica | && y || usan cortocircuito. | Preserva efectos y comportamiento esperado. |
| Ternario | Solo se evalúa una rama. | Conservación semántica. |
| Temporales | Pool con acquire/release y verificación de vida. | Cumple reciclaje sin eliminar cálculos. |
| Etiquetas | Únicas por unidad; no se reciclan. | Evita destinos ambiguos. |
| Listas | Índices lógicos en la IR. | La escala física pertenece al backend. |
| Objetos | Referencias de 8 bytes y campos por offset. | Modelo abstracto claro. |
| Closures | Etiqueta más entorno explícito. | Hace visible el acceso al entorno de definición. |
| Capturas | Access link o entorno, nunca control link. | Respeta alcance léxico. |
| Layout | Modelo abstracto de 64 bits documentado. | El enunciado no define arquitectura destino. |
| Salida inválida | No publicar TAC parcial como aceptado. | Evita ocultar un nodo sin lowering. |
| Perfil JSON | No se usa para codificar instrucciones TAC. | El perfil conserva su función semántica. |
| GUI | Solo presenta CompilationResult. | No duplica reglas del compilador. |

## Decisión importante: no implementar GDA como requisito

Los apuntes explican GDA y números de valor para compartir subexpresiones
puras. El enunciado actual no lo exige. Se excluye del alcance mínimo porque:

- una llamada puede tener efectos laterales;
- una escritura invalida valores anteriores;
- una carga puede depender de alias;
- sin versiones SSA o memoria, compartir puede cambiar el programa.

El reciclaje de temporales sí se implementa. Reciclar un nombre después del
último uso no equivale a eliminar o compartir una operación.

## Modelo de datos propuesto

### Tipos y tamaños

| Tipo | Tamaño | Alineación |
|---|---:|---:|
| boolean | 1 | 1 |
| integer | 4 | 4 |
| float | 8 | 8 |
| string | 8 | 8 |
| lista | 8 | 8 |
| objeto/clase | 8 | 8 |
| función/closure | 8 | 8 |
| referencia desconocida | 8 | 8 |

Las cifras son parte de una máquina abstracta, no prometen un ABI real.

### Registros de activación

Todo frame lógico incluye:

- dirección o etiqueta de retorno;
- enlace de control;
- enlace de acceso;
- área de resultado;
- parámetros ocultos;
- parámetros declarados;
- locales;
- slots de temporales.

Los offsets son relativos a la base del frame y están alineados. No se generan
prólogos, epílogos ni registros de CPU en este proyecto.

### Almacenamiento

| Clase | Uso |
|---|---|
| static | globales y etiquetas de programa |
| parameter | parámetros declarados u ocultos |
| local | variables del frame |
| field | contenido de una instancia |
| captured | valor o referencia guardada en entorno |
| temporary | slot reutilizable del frame |

## Reglas para control de flujo

- while: continue vuelve a la condición.
- do-while: continue va a la condición final.
- for: continue va a la actualización.
- foreach: continue va al incremento del índice.
- break usa el bucle más cercano mientras se conserve la regla semántica
  vigente.
- switch evalúa su expresión una sola vez.
- Los casos de switch conservan orden fuente.
- Toda etiqueta referenciada debe definirse.

## Reglas para funciones y closures

- Las funciones globales y métodos reciben etiquetas antes de generar cuerpos.
- La recursión usa la misma etiqueta en cada llamada.
- Los argumentos se evalúan de izquierda a derecha.
- this es parámetro oculto de método y constructor.
- env es parámetro oculto de una función con capturas.
- El control link apunta al caller dinámico.
- El access link o entorno apunta al contenedor léxico.
- Una captura que sobrevive al frame se representa en un entorno de heap
  abstracto.
- No se implementa administración real ni recolección de ese heap.

## Reglas para clases, objetos y listas

- OBJECT_NEW reserva el tamaño calculado por ClassLayout.
- Los campos heredados se ubican antes de los propios.
- Los métodos tienen etiquetas; no ocupan bytes dentro del objeto.
- Una clase sin constructor explícito conserva el constructor vacío ya aceptado
  por semántica.
- LIST_NEW almacena una longitud lógica.
- LIST_GET y LIST_SET usan índice lógico.
- La comprobación de tipo de índice ocurre en semántica.
- Los límites de índice pueden quedar como chequeo abstracto de runtime si el
  profesor lo solicita; el valor dinámico no siempre se conoce al compilar.

## Preguntas pendientes para el profesor

| Pregunta | Riesgo | Decisión provisional |
|---|---|---|
| ¿break puede salir de switch o solo de bucles? | Cambia pilas de destinos y casos válidos. | Mantener la regla actual: solo bucles. |
| ¿switch tiene caída entre casos o break implícito? | Cambia el TAC de cada case. | Conservar fall-through. |
| ¿switch conserva la condición booleana exigida por la fase semántica actual o acepta otro discriminante? | Puede requerir cambiar semántica y comparación de casos. | Conservar boolean hasta recibir corrección. |
| ¿Se espera cuádruplo, tripleta o solo texto TAC? | Puede cambiar entregable visible. | Cuádruplo interno y texto visible. |
| ¿Los offsets deben ser bytes reales o slots abstractos? | Afecta layouts y demostración. | Bytes de máquina abstracta de 64 bits. |
| ¿Existe una arquitectura o ABI objetivo? | Cambia tamaños y frames. | Ninguna hasta confirmación. |
| ¿Closure debe usar static link o entorno heap explícito? | Afecta instrucciones y tabla. | Entorno explícito para escapes y distancia léxica registrada. |
| ¿Se evalúan argumentos de izquierda a derecha? | Afecta efectos laterales. | Sí. |
| ¿El método llamado se resuelve estáticamente o requiere despacho dinámico? | Requiere vtable si es dinámico. | Etiqueta resuelta por tipo estático. |
| ¿Se exige manejo de límites en listas? | Puede requerir BOUNDS_CHECK. | Registrar instrucción abstracta si se solicita. |
| ¿Qué semántica debe tener try/catch sin throw en la gramática? | No hay fuente explícita de excepción. | IR de alto nivel o diagnóstico documentado. |
| ¿Una función no void debe retornar en todos los caminos? | La semántica actual valida cada return, pero no demuestra cobertura de caminos. | No inventar un valor; consultar antes de endurecer semántica o codegen. |
| ¿Las extensiones foreach, herencia y try/catch serán evaluadas? | Aumenta alcance. | Cubrir después del mínimo, sin TAC parcial silencioso. |
| ¿Se debe guardar automáticamente un archivo .tac? | Afecta UX y pruebas. | Mostrar siempre; exportar solo a solicitud. |

Cuando el profesor responda:

1. agregar fecha y respuesta a este documento;
2. actualizar DISENO_TAC.md;
3. actualizar la matriz y fixtures;
4. hacerlo dentro del bloque que todavía esté abierto.

## Alcance no incluido

- optimización de subexpresiones;
- SSA;
- bloques básicos y CFG como entregable visual;
- código assembler u objeto;
- selección de instrucciones;
- registros físicos y spilling real;
- ABI de una plataforma;
- ejecución nativa del TAC;
- recolector de basura;
- análisis de escape avanzado;
- optimizaciones de tail call o inlining.

Estos temas pueden usar la IR en fases posteriores, pero no deben desplazar los
100 puntos actuales.

## Reglas para fixtures

- Un caso de generación positivo debe ser sintáctica y semánticamente válido.
- Un caso semántico negativo debe tener sintaxis válida.
- Un caso de parser negativo no demuestra un error del generador.
- Cada fixture indica IDs de la matriz y resultado esperado.
- Las pruebas deben confirmar ausencia de TAC cuando una fase anterior falla.
- Los golden TAC se usan solo donde el orden textual forma parte de la
  evidencia.
- Las demás pruebas inspeccionan opcodes, operandos, etiquetas y layouts.
- Un programa que activa un warning debe demostrar si TAC se produce.
- Toda alternativa de la gramática tiene handler o diagnóstico explícito.

## Reglas para cambios a la gramática o perfil

La fase de código intermedio no necesita cambiar Compiscript.g4. Si surge una
necesidad:

1. demostrar que es un defecto sintáctico, no comodidad de codegen;
2. revisar todas las pruebas de frontend;
3. actualizar deliberadamente el fingerprint;
4. revisar el perfil semántico completo;
5. registrar el motivo y el commit.

No se actualiza el hash únicamente para ocultar una incompatibilidad.

## Definición de una decisión cerrada

Una decisión está cerrada cuando:

- tiene fuente o respuesta del profesor;
- está reflejada en diseño, implementación y pruebas;
- no contradice la semántica vigente;
- aparece en la matriz si afecta calificación.

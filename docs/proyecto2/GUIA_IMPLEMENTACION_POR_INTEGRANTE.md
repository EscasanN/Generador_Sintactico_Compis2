# Guía detallada de implementación por integrante — Proyecto 2

## Propósito

Esta guía convierte la división general en contratos de trabajo verificables.
No afirma que los módulos ya existan. Cada bloque debe implementar sus archivos,
probarlos, documentarlos e integrarlos antes de crear la rama siguiente.

## Forma de trabajo

~~~text
Rama de integración aceptada
    ↓
el integrante crea su rama
    ↓
implementa API + pruebas + documentación
    ↓
abre revisión y corrige
    ↓
se integra y congela el contrato público
    ↓
comienza el siguiente bloque
~~~

Reglas:

1. Las pruebas de la fase semántica siempre se consideran regresiones.
2. Los módulos públicos usan type hints y resultados inmutables.
3. Los errores del usuario se acumulan como diagnósticos; los contratos
   inválidos de programación lanzan errores claros o diagnósticos IR.
4. La representación estructurada es la fuente de verdad, no el texto TAC.
5. Ningún bloque introduce dependencias de Qt fuera de la interfaz.
6. Las APIs públicas se documentan antes del handoff.

## Contratos existentes que se conservan

### Frontend

- analyze_with_g4 analiza una gramática y conserva árbol común y nativo.
- ParseTreeNode expone symbol, children, rule_name, alternative, token_type,
  text y ubicación.
- AntlrAnalysisResult.accepted indica ausencia de errores léxicos y sintácticos.

### Semántica

- analyze_semantics_with_g4 ejecuta sintaxis y luego semántica.
- SemanticRunResult conserva syntax_result y semantic_result.
- SemanticAnalysisResult expone diagnósticos, tabla de símbolos, valor final y
  estadísticas.
- SymbolTable conserva scopes cerrados.
- SemanticValue puede referenciar el Symbol resuelto.

La generación se agrega mediante compile_compiscript. La API anterior sigue
disponible para pruebas y diagnóstico aislado.

# Bloque 1 — Daniel Chet

## Objetivo

Entregar una IR completa y verificable, más el lowering de expresiones y el
algoritmo de temporales, sin depender de cambios futuros en la semántica.

## Archivos

~~~text
src/codegen/__init__.py
src/codegen/contracts.py
src/codegen/ir.py
src/codegen/builder.py
src/codegen/names.py
src/codegen/verifier.py
src/codegen/formatter.py
src/codegen/expression_lowering.py
tests/codegen/test_ir.py
tests/codegen/test_builder.py
tests/codegen/test_temporaries.py
tests/codegen/test_verifier.py
tests/codegen/test_expression_lowering.py
docs/proyecto2/DISENO_TAC.md
~~~

src/codegen/__init__.py debe permanecer pequeño. No necesita reexportar cada
clase; así los bloques posteriores pueden agregar módulos sin editar un archivo
cerrado.

## contracts.py

Protocolos propuestos:

~~~python
class SemanticFacts(Protocol):
    def value_for(self, node: ParseTreeNode) -> SemanticValue: ...
    def symbol_for(self, node: ParseTreeNode) -> Symbol | None: ...
    def scope_for(self, node: ParseTreeNode) -> Scope: ...
    def address_for(self, symbol: Symbol) -> Address: ...
    def member_offset(self, owner: Type, name: str) -> int: ...
    def lexical_access(self, node: ParseTreeNode, symbol: Symbol) -> LexicalAccess: ...
~~~

Daniel prueba contra un FakeSemanticFacts. Nadissa implementa el adaptador real
sin cambiar estas firmas.

ValueRef propuesto:

~~~text
ValueRef
├── operand
├── type
├── owns_temporary
└── release(builder)
~~~

La propiedad owns_temporary evita liberar símbolos o constantes como si fueran
temporales.

## ir.py

Tipos públicos mínimos:

| Tipo | Responsabilidad |
|---|---|
| OpCode | lista cerrada de instrucciones válidas |
| OperandKind | constante, símbolo, temporal, etiqueta u offset |
| Operand | valor tipado e inmutable |
| Instruction | cuádruplo más ubicación fuente |
| IRProcedure | etiqueta, parámetros e instrucciones |
| IRProgram | código global y procedimientos |

Toda instrucción se crea mediante constructores validados o IRBuilder. No se
permiten strings libres como opcode.

## names.py

### LabelFactory

- next(prefix) retorna una etiqueta no repetida;
- el contador se reinicia por unidad de compilación;
- las etiquetas no se reciclan.

### TemporaryPool

API propuesta:

~~~text
acquire(type) → Operand temporal
release(temp) → None
is_active(temp) → bool
active_count → int
peak_active → int
~~~

Debe rechazar:

- liberar un símbolo;
- liberar dos veces;
- liberar un temporal de otro pool;
- usar un nombre libre como activo sin acquire.

## builder.py

IRBuilder centraliza:

- procedimiento actual;
- emisión de instrucciones;
- definición de etiquetas;
- adquisición y liberación de temporales;
- asociación de SourceLocation;
- contador de PARAM pendiente si se decide validarlo durante emisión.

API orientativa:

~~~text
begin_procedure(label, parameters)
end_procedure()
emit(opcode, arg1=None, arg2=None, result=None, location=None)
mark(label, location=None)
jump(label, location=None)
branch_false(condition, label, location=None)
temporary(type)
release(value)
build() → IRProgram
~~~

## verifier.py

Debe recorrer cada procedimiento de forma independiente y producir una lista de
IRDiagnostic. Reglas mínimas:

- opcode y aridad;
- temporal definido antes de uso;
- etiqueta única;
- salto con destino existente;
- procedimiento cerrado;
- PARAM coherente con CALL;
- ubicación fuente para instrucciones derivadas de nodos;
- temporales sin colisiones vivas.

Las pruebas construyen IR válida e inválida manualmente.

## formatter.py

El formato:

- es determinista;
- preserva orden;
- no incluye direcciones de memoria de Python;
- muestra procedimientos y etiquetas;
- puede incluir comentarios de línea fuente sin afectar la IR.

Una misma IR debe producir exactamente el mismo texto en ejecuciones
consecutivas.

## expression_lowering.py

ExpressionLowerer recibe IRBuilder y SemanticFacts. Cubre:

- literales primitivos y null;
- identificadores locales, globales y capturados;
- +, -, *, /, %;
- negación numérica y lógica;
- ==, !=, <, <=, >, >=;
- && y || con cortocircuito;
- ternario con una sola rama evaluada;
- asignación como sentencia y expresión;
- llamadas, índices y miembros mediante primitivas que Dulce completará;
- liberación después del último consumo.

No revalida tipos. Si SemanticFacts no tiene un hecho requerido, reporta un
error interno con ubicación.

## Pruebas del bloque 1

- igualdad e inmutabilidad de operandos e instrucciones;
- catálogo completo y aridad;
- formato estable;
- temporal nuevo cuando todos están activos;
- reutilización después de release;
- error por doble release y uso después de release;
- peak_active correcto;
- precedencia heredada del árbol;
- evaluación izquierda a derecha;
- cortocircuito;
- comparación y asignación;
- ternario;
- verifier detecta temporal y etiqueta inválidos.

## Puerta Daniel → Nadissa

- [ ] Todos los tipos públicos están documentados.
- [ ] FakeSemanticFacts demuestra que no depende de futuras clases concretas.
- [ ] Las pruebas del bloque pasan sin Java ni PyQt6.
- [ ] DISENO_TAC.md coincide con opcodes y formato.
- [ ] No se modificó la fase semántica.

# Bloque 2 — Nadissa Vela

## Objetivo

Conectar la información semántica existente con los contratos de codegen y
crear la tabla extendida y los registros de activación.

## Archivos

~~~text
src/semantic/results.py
src/semantic/evaluator.py
src/semantic/antlr_listener.py
src/codegen/semantic_facts.py
src/codegen/layout.py
src/codegen/activation.py
tests/semantic/test_codegen_annotations.py
tests/codegen/test_semantic_facts.py
tests/codegen/test_layout.py
tests/codegen/test_activation.py
~~~

## Anotaciones semánticas

Agregar SemanticAnnotations con mapas inmutables:

~~~text
values_by_node
symbols_by_node
scopes_by_node
~~~

Procedimiento:

1. conservar context.results como hasta ahora;
2. registrar el scope activo después de acciones phase=enter;
3. derivar symbols_by_node de SemanticValue.symbol y símbolos predeclarados;
4. copiar los mapas al resultado final;
5. limpiar estado mutable al terminar o abortar.

La construcción manual con SemanticEvaluator y la ejecución real con
SemanticTreeListener deben producir la misma forma de anotaciones.

Los nuevos campos tienen valores por defecto para no romper pruebas que crean
SemanticAnalysisResult directamente.

## semantic_facts.py

SemanticFactsIndex implementa el protocolo de Daniel:

- consulta por identidad del mismo ParseTreeNode retenido por syntax_result;
- devuelve UNKNOWN o un error interno explícito según el contrato;
- localiza el scope donde se declaró cada Symbol;
- determina si un acceso es local, global, campo o no local;
- calcula distancia léxica entre scopes de función.

No vuelve a buscar por nombre cuando ya existe un Symbol resuelto.

## layout.py

Tipos propuestos:

| Tipo | Responsabilidad |
|---|---|
| StorageClass | static, parameter, local, field, captured, temporary |
| TypeLayout | tamaño y alineación |
| SymbolLayout | Symbol, clase, offset, tamaño, alineación, etiqueta y nivel |
| ClassLayout | clase, tamaño total, campos y herencia |
| SymbolLayoutTable | vista combinada de SymbolTable y layouts |
| LayoutBuilder | asignación alineada y detección de solapamiento |

Regla de alineación:

~~~text
aligned = ceil(current / alignment) * alignment
~~~

Los campos de una superclase se colocan antes que los nuevos campos. Un método
no ocupa espacio de instancia; recibe una etiqueta.

## activation.py

Tipos propuestos:

| Tipo | Responsabilidad |
|---|---|
| FrameSlotKind | header, parameter, local, captured, temporary |
| FrameSlot | nombre, offset, tamaño, alineación y tipo |
| ActivationRecordLayout | función, nivel, header, slots y tamaño |
| ActivationRecordBuilder | reserva ordenada y finalización |
| LexicalAccess | local/global/captured, profundidad y offset |

El header abstracto incluye:

- return_address;
- control_link;
- access_link;
- return_value.

Métodos y closures agregan this o env como parámetros ocultos. El builder debe
permitir reservar slots temporales al conocer peak_active.

## Capturas

Una referencia es captura cuando:

1. se usa dentro de una función;
2. su Symbol se declaró fuera del scope de esa función;
3. no es global ni miembro resuelto mediante this.

Se calcula la distancia de enlaces de acceso. Si una closure puede escapar, su
entorno se marca HEAP_ENV. El proyecto registra esta decisión; no administra
memoria real.

## Pruebas del bloque 2

- mapas inmutables;
- valor y Symbol correctos para identificadores con shadowing;
- scope correcto de bloque, función y clase;
- compatibilidad de SemanticAnalysisResult anterior;
- tamaños y alineaciones de cada tipo;
- dos locales sin solapamiento;
- parámetros y locales con offsets distintos;
- campos heredados;
- etiquetas únicas y deterministas;
- frame con todos los campos obligatorios;
- control link diferente de access link;
- una captura simple y otra a dos niveles;
- función recursiva sin captura falsa;
- slots temporales según peak_active.

## Puerta Nadissa → Dulce

- [ ] Regresiones semánticas completas pasan.
- [ ] Un programa real produce anotaciones consultables.
- [ ] SymbolLayoutTable contiene todos los símbolos relevantes.
- [ ] ActivationRecordLayout valida alineación y no solapamiento.
- [ ] SemanticFactsIndex satisface el protocolo de Daniel.
- [ ] No se emitieron sentencias TAC en este bloque.

# Bloque 3 — Dulce Ambrosio

## Objetivo

Implementar el lowering de programas completos y el pipeline público de
compilación.

## Archivos

~~~text
src/codegen/statements.py
src/codegen/control_flow.py
src/codegen/callables.py
src/codegen/objects.py
src/codegen/generator.py
src/codegen/results.py
src/codegen/pipeline.py
tests/codegen/test_statements.py
tests/codegen/test_control_flow.py
tests/codegen/test_callables.py
tests/codegen/test_closures.py
tests/codegen/test_objects.py
tests/codegen/test_lists.py
tests/codegen/test_pipeline.py
~~~

## generator.py

CompiscriptCodeGenerator coordina:

- árbol común;
- SemanticFactsIndex;
- SymbolLayoutTable;
- layouts de clase y activación;
- IRBuilder y ExpressionLowerer;
- pilas de control;
- procedimiento y clase actuales.

Estado mínimo:

~~~text
break_targets
continue_targets
function_stack
class_stack
~~~

Cada dispatcher usa rule_name o alternative del nodo. No analiza source text
para reconstruir estructura.

Debe existir una comprobación de cobertura: una alternativa de sentencia o
expresión alcanzada sin handler produce IRGEN-UNSUPPORTED-NODE con ubicación.

## statements.py y control_flow.py

### Declaraciones

- reservar SymbolLayout;
- emitir inicializador si existe;
- copiar resultado a la dirección del símbolo;
- no asignar automáticamente un valor inventado salvo que Compiscript defina
  un valor por defecto.

### Asignaciones

- variable: COPY;
- lista: LIST_SET;
- campo: FIELD_SET;
- expresión de asignación: devolver el valor asignado según la semántica
  confirmada.

### Control

Usar las plantillas de DISENO_TAC.md. Los destinos:

| Construcción | break | continue |
|---|---|---|
| while | salida | condición |
| do-while | salida | condición final |
| for | salida | actualización |
| foreach | salida | incremento de índice |

Un bucle interno apila sus destinos y los retira al salir, aunque ocurra un
error de generación.

Switch evalúa el discriminante una vez y conserva orden de casos. La semántica
de break se ajusta a la decisión registrada antes de cerrar el bloque.

## callables.py

Responsabilidades:

- preasignar etiquetas a funciones y métodos;
- generar un IRProcedure por cuerpo;
- definir parámetros declarados y ocultos;
- emitir PARAM en orden fuente;
- distinguir llamada void y con resultado;
- emitir RETURN compatible;
- agregar retorno void final cuando corresponda;
- permitir referencia recursiva antes de terminar el cuerpo;
- construir entornos y CLOSURE para funciones anidadas;
- generar acceso no local mediante LexicalAccess.

La recursión se demuestra con un .cps real, no únicamente llamando helpers.

## objects.py

Responsabilidades:

- construir ClassLayout;
- reservar OBJECT_NEW;
- localizar constructor explícito o implícito;
- pasar this como primer parámetro;
- leer y escribir campos por offset;
- invocar métodos con this;
- mantener campos heredados antes de campos propios;
- resolver etiqueta de método a partir del Symbol semántico.

No se implementa despacho dinámico completo si el lenguaje no lo exige. La
convención adoptada debe quedar documentada.

## Listas

- LIST_NEW con cantidad conocida del literal;
- LIST_SET por elemento de izquierda a derecha;
- LIST_GET para indexación;
- LIST_SET para asignación indexada si la gramática la permite;
- LIST_LEN para foreach;
- el tipo/tamaño del elemento proviene de semántica.

## results.py

IntermediateCodeResult debe ser inmutable y exponer:

- program opcional;
- texto;
- diagnósticos;
- SymbolLayoutTable;
- layouts de activación;
- estadísticas: instrucciones, procedimientos, temporales creados y pico;
- accepted.

accepted requiere programa presente, cero errores IR y verificación exitosa.

## pipeline.py

Orden estricto:

1. analyze_semantics_with_g4;
2. si falla sintaxis, devolver sin semántica/codegen;
3. si falla semántica, devolver sin codegen;
4. construir hechos y layouts;
5. generar IR;
6. verificar;
7. formatear;
8. devolver CompilationResult.

No se captura una excepción inesperada como ACCEPT. Los errores de contrato se
convierten en diagnósticos IR o se propagan como CodegenError según sean
recuperables.

## Pruebas del bloque 3

Casos positivos y negativos para:

- declaración y asignación;
- if con y sin else;
- while, do-while y las cuatro formas de for de la gramática;
- switch con casos y default;
- break/continue anidados;
- función void y con retorno;
- parámetros y llamada;
- recursión;
- función anidada con captura;
- closure a dos niveles;
- objeto, constructor, campo, método y this;
- lista vacía, no vacía, carga y store;
- frontend o semántica inválidos sin TAC;
- nodo sin soporte con diagnóstico;
- salida completa verificada.

## Puerta Dulce → Nelson

- [ ] compile_compiscript es la única API integral necesaria por consumidores.
- [ ] Toda salida aceptada pasa IRVerifier.
- [ ] Errores previos impiden generar TAC.
- [ ] La matriz mínima funciona desde archivos .cps.
- [ ] No hay dependencias de PyQt6.
- [ ] APIs y ejemplos están documentados.

# Bloque 4 — Nelson Escalante

## Objetivo

Presentar el pipeline completo, crear evidencia reproducible y cerrar la
entrega sin introducir reglas de compilación en la interfaz.

## Archivos

~~~text
src/main.py
src/gui/app.py
src/gui/codegen_results.py
src/gui/semantic_results.py
tests/test_main_cli.py
tests/gui/test_cps_workflow.py
tests/gui/test_codegen_results.py
tests/cps/codegen/
README.md
docs/proyecto2/
~~~

## IDE

El worker invoca compile_compiscript. El resultado se presenta en pestañas:

1. árbol sintáctico;
2. semántica;
3. código intermedio;
4. tabla extendida y activaciones;
5. resumen/diagnósticos.

Requisitos:

- botón deshabilitado mientras compila;
- resultado anterior se limpia al comenzar;
- un error nunca deja TAC viejo visible como si fuera actual;
- TAC usa fuente monoespaciada, búsqueda o copia;
- tabla muestra almacenamiento, offset, tamaño, etiqueta y nivel;
- frames muestran header, parámetros, locales, temporales y tamaño total;
- el hilo GUI no calcula ni modifica IR.

## CLI

Interfaz propuesta:

~~~powershell
python -m src.main --cps programa.cps --emit-tac
python -m src.main --cps programa.cps --emit-tac salida.tac
~~~

Sin ruta, imprime TAC. Con ruta, guarda UTF-8 y muestra el destino. Los códigos:

- 0: compilación aceptada y TAC verificado;
- 1: rechazo léxico, sintáctico, semántico o IR;
- 2: lectura, configuración o dependencia.

## Fixtures

Estructura:

~~~text
tests/cps/codegen/
├── validos/
├── invalidos/
└── esperados/
~~~

Cada archivo empieza con comentarios que indican IDs de la matriz. Los golden
.tac se reservan para ejemplos representativos; el resto prueba la IR
estructurada para no volver frágil toda la suite ante cambios de formato.

Un caso negativo semántico confirma:

- REJECT;
- diagnósticos presentes;
- intermediate_result ausente.

Un caso interno de IR inválida pertenece a tests/codegen y confirma el código
del diagnóstico del verifier.

## Documentación final

Actualizar:

- README principal;
- estado de las casillas del plan;
- matriz con ruta exacta de evidencia;
- decisiones realmente adoptadas;
- comandos de instalación y ejecución;
- guía de demostración;
- limitaciones conocidas.

No marcar como implementado algo cubierto solo por un diseño o una prueba
saltada.

## Puerta Nelson → entrega

- [ ] El IDE compila una demostración completa.
- [ ] La CLI imprime el mismo TAC.
- [ ] Una entrada inválida muestra error y ningún TAC.
- [ ] Tabla extendida y frames son visibles.
- [ ] Suite completa pasa desde un clon limpio.
- [ ] La documentación coincide con el comportamiento.
- [ ] Los commits distinguen a los cuatro integrantes.

# Checklist global de integración

- [ ] Compiscript.g4 conserva su fingerprint o se actualiza deliberadamente.
- [ ] La suite de análisis semántico no pierde cobertura.
- [ ] Todos los opcodes están documentados y probados.
- [ ] Todos los nodos mínimos tienen lowering.
- [ ] Temporales y etiquetas pasan verificación.
- [ ] Capturas usan acceso léxico, no el caller por accidente.
- [ ] Los offsets están alineados y no se solapan.
- [ ] IDE y CLI consumen la misma API.
- [ ] No hay archivos generados o cachés en Git.
- [ ] La matriz tiene evidencia localizable.

# Arquitectura — generación de código intermedio

## Objetivo arquitectónico

La nueva fase se agrega después del análisis semántico sin romper la entrega
anterior. El frontend conserva la responsabilidad de aceptar o rechazar el
programa; el generador recibe únicamente un árbol válido, hechos semánticos y
una tabla de símbolos persistente.

El cierre final se documenta en [AUDITORIA_FINAL.md](AUDITORIA_FINAL.md). Codegen
añade símbolos y scopes internos para receptores y constructores implícitos sin
mutar el árbol de scopes semántico. Los layouts de clases se consultan por
identidad; sus etiquetas únicas indexan la colección pública. Las referencias
textuales ambiguas se rechazan.

El análisis de capturas propaga dependencias de entorno hasta un punto fijo.
Las instancias locales retienen sus entornos; los procedimientos de métodos
incluyen el offset necesario para ligar también el entorno con `METHOD_REF`.
El verificador comprueba firmas conocidas y prohíbe acceder directamente a otro
frame. La validación de salidas no `void` ocurre antes de publicar IR.

El worker del IDE captura una revisión de documento. Cambiar texto o identidad
invalida resultados y exportación; señales atrasadas no sustituyen el documento
actual. El resumen usa la ruta del resultado de compilación.

## Flujo completo

~~~text
Fuente .cps
   ↓
src/antlr_mode/runner.py
   ├── genera o reutiliza Lexer/Parser
   ├── analiza con la regla program
   └── produce ParseTreeNode + árbol nativo
   ↓
src/semantic/antlr_adapter.py
   ├── valida el perfil semántico
   ├── recorre con SemanticTreeListener
   └── produce SemanticAnalysisResult
   ↓
¿sintaxis y semántica aceptadas?
   ├── no → diagnósticos; no existe salida TAC
   └── sí
        ↓
src/codegen/semantic_facts.py
   ├── tipos y símbolos por nodo
   ├── scope léxico por nodo
   └── distancia a declaraciones no locales
        ↓
src/codegen/layout.py + activation.py
   ├── tamaños, alineaciones y offsets
   ├── etiquetas de funciones y métodos
   └── registros de activación y entornos capturados
        ↓
src/codegen/generator.py
   ├── expresiones y asignaciones
   ├── control de flujo
   ├── funciones y closures
   ├── clases y objetos
   └── listas
        ↓
IRProgram de cuádruplos
        ↓
src/codegen/verifier.py
   ├── definición antes de uso
   ├── destinos de salto válidos
   ├── temporales vivos sin colisión
   └── forma y aridad de instrucciones
        ↓
IntermediateCodeResult
   ├── TAC textual
   ├── tabla de símbolos extendida
   ├── layouts de activación
   └── diagnósticos de generación
        ↓
CLI o IDE
~~~

## Contratos públicos

### Anotaciones semánticas

SemanticAnalysisResult se amplía de forma compatible con un índice inmutable:

~~~text
SemanticAnnotations
├── values_by_node: id(ParseTreeNode) → SemanticValue
├── symbols_by_node: id(ParseTreeNode) → Symbol
└── scopes_by_node: id(ParseTreeNode) → Scope
~~~

Los campos existentes de SemanticAnalysisResult conservan su significado y sus
valores por defecto. Las pruebas de la entrega anterior deben seguir pasando.

### Representación intermedia

~~~text
IRProgram
├── global_code: tuple[Instruction, ...]
└── procedures: tuple[IRProcedure, ...]

IRProcedure
├── label
├── parameters
└── instructions

Instruction
├── opcode
├── arg1
├── arg2
├── result
└── source_location
~~~

El modelo detallado y el catálogo de instrucciones están en
[DISENO_TAC.md](DISENO_TAC.md).

### Resultado de generación

~~~text
IntermediateCodeResult
├── program: IRProgram | None
├── diagnostics
├── symbol_layouts
├── activation_records
├── text
└── accepted
~~~

Un resultado aceptado siempre contiene un IRProgram verificado. Un error
interno de lowering, un temporal sin definición o una etiqueta inexistente
produce un diagnóstico de código intermedio y evita marcar la compilación como
aceptada.

### Resultado integral

~~~text
CompilationResult
├── syntax_result
├── semantic_result
├── intermediate_result
└── accepted
~~~

La función pública (src/codegen/pipeline.py) es:

~~~python
compile_compiscript(
    source: str,
    source_path: str | Path | None = None,
    *,
    grammar_path: str | Path = GRAMMAR_PATH,
    profile_path: str | Path = PROFILE_PATH,
) -> CompilationResult
~~~

Esta función envuelve analyze_semantics_with_g4; no sustituye ni cambia esa API.

## Paquetes

~~~text
src/
├── antlr_mode/                         # existente; no se reescribe
├── semantic/                           # existente; solo anotaciones compatibles
├── codegen/
│   ├── __init__.py
│   ├── contracts.py                    # protocolos consumidos por el lowering
│   ├── ir.py                           # operandos, instrucciones y programa
│   ├── builder.py                      # emisión controlada
│   ├── names.py                        # temporales y etiquetas
│   ├── verifier.py                     # invariantes de IR
│   ├── formatter.py                    # TAC textual estable
│   ├── expression_lowering.py
│   ├── semantic_facts.py
│   ├── layout.py
│   ├── activation.py
│   ├── statements.py
│   ├── control_flow.py
│   ├── callables.py
│   ├── objects.py
│   ├── generator.py
│   ├── results.py
│   └── pipeline.py
├── gui/
│   ├── app.py                          # ventana, CompilationWorker (QThread)
│   ├── codegen_results.py              # TacView, LayoutPanel, DiagnosticsTable
│   ├── semantic_results.py             # diagnósticos y tabla por ámbito
│   └── parse_tree_view.py              # árbol navegable
└── main.py                             # CLI: --cps, --emit-tac, --show-layout

tests/
├── codegen/
├── cps/codegen/
│   ├── validos/
│   ├── invalidos/
│   └── esperados/
└── gui/
~~~

Los nombres coinciden con el código entregado. La única desviación registrada
es tests/codegen/test_control_flow_lowering.py (bloque 3), renombrado para no
chocar con tests/semantic/test_control_flow.py.

## Presentación: CLI e IDE

Ambos consumidores llaman a compile_compiscript y no contienen reglas de
traducción:

~~~text
python -m src.main --cps x.cps [--emit-tac [RUTA]] [--show-layout]
    └── _run_cps_cli → compile_compiscript → reporte por fase
                                            → tac_document(result.tac)

python -m src.main  (IDE)
    └── MainWindow._run_compilation
          ├── limpia resultados anteriores y deshabilita Compilar
          └── CompilationWorker (QThread) → compile_compiscript
                └── señal completed(bundle) → hilo de Qt
                      ├── TacView           (OUT-03)
                      ├── LayoutPanel       (OUT-04)
                      ├── DiagnosticsTable  (OUT-05)
                      └── árbol + panel semántico existentes
~~~

- El texto del TAC es el mismo en ambos: tac_document agrega solo el salto de
  línea final y los archivos se escriben en UTF-8 con LF.
- Un rechazo en cualquier fase deja intermediate_result sin programa; las vistas
  muestran el motivo y nunca conservan el TAC de una compilación anterior.
- La CLI separa stdout (solo TAC con --emit-tac) de stderr (diagnósticos), para
  poder redirigir la salida.

## Invariantes de la arquitectura

1. Sintaxis siempre se ejecuta antes que semántica.
2. TAC solo se genera si sintaxis y semántica están aceptadas.
3. El generador no vuelve a validar tipos ni nombres; consume hechos ya
   comprobados.
4. Cada instrucción conserva ubicación fuente para diagnóstico y defensa.
5. Todo temporal se define antes de usarse y solo se recicla cuando dejó de
   estar vivo.
6. Toda etiqueta referenciada se emite exactamente una vez.
7. La evaluación respeta el orden de izquierda a derecha y el cortocircuito
   lógico.
8. Los enlaces de control y de acceso se modelan por separado.
9. El formato textual se deriva de la IR estructurada; no es la fuente de
   verdad.
10. La GUI consume resultados públicos y no implementa reglas de traducción.

## Componentes que no deben modificarse sin una razón documentada

- Compiscript.g4: la generación de TAC es una fase posterior a la gramática.
- semantic_profiles/compiscript.semantic.json: solo cambia si cambia
  intencionalmente la semántica o la gramática.
- El contrato público de analyze_semantics_with_g4.
- La etiqueta Git entrega-semantica-100.

## Relación con los apuntes

La arquitectura adopta de los apuntes:

- cuádruplos por su resultado explícito y referencias estables;
- emisión en postorden para expresiones;
- etiquetas y saltos para control estructurado;
- offsets calculados con tamaño y alineación;
- registros de activación con parámetros, retorno, enlaces, locales y
  temporales;
- enlace de acceso para funciones anidadas.

No se incorpora un GDA ni numeración de valores en el alcance mínimo. Eso es
optimización y requiere controlar efectos laterales, alias y versiones de
memoria; implementarlo aquí aumentaría el riesgo sin ser requisito del
enunciado.

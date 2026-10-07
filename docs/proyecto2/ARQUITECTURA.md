# Arquitectura propuesta — generación de código intermedio

## Objetivo arquitectónico

La nueva fase se agrega después del análisis semántico sin romper la entrega
anterior. El frontend conserva la responsabilidad de aceptar o rechazar el
programa; el generador recibe únicamente un árbol válido, hechos semánticos y
una tabla de símbolos persistente.

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

## Contratos públicos propuestos

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

La función pública propuesta es:

~~~python
compile_compiscript(
    source: str,
    source_path: str | Path | None = None,
) -> CompilationResult
~~~

Esta función envuelve analyze_semantics_with_g4; no sustituye ni cambia esa API.

## Paquetes propuestos

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
│   ├── app.py
│   └── codegen_results.py
└── main.py

tests/
├── codegen/
├── cps/codegen/
│   ├── validos/
│   ├── invalidos/
│   └── esperados/
└── gui/
~~~

Los nombres son el contrato de planificación. Si durante el primer bloque se
decide combinar dos módulos, el cambio debe registrarse antes de que otro
integrante consuma la API.

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

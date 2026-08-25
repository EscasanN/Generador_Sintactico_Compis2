# División del trabajo — Fase 3

Esta es la vista resumida. Los archivos, clases, funciones y pruebas están en la
[guía detallada](GUIA_IMPLEMENTACION_POR_INTEGRANTE.md).

## Equipo

| Integrante | Frente | Rama |
|---|---|---|
| Daniel Chet | Tipos, valores y acciones de expresiones | `feature/fase3-types-expressions` |
| Dulce Ambrosio | Frontend ANTLR genérico y árbol común | `feature/fase3-antlr-frontend` |
| Nadissa Vela | Símbolos, perfiles y evaluador semántico | `feature/fase3-semantic-engine` |
| Nelson Escalante | IDE, perfil Compiscript e integración | `feature/fase3-ide-integration` |

Ninguna persona queda asignada únicamente a documentación o pruebas.

## Trabajo común inicial

Antes de desarrollar semántica:

- revisar la base multimodo ya implementada;
- confirmar que una gramática es dato de entrada;
- congelar contratos de diagnóstico, tipo, símbolo, perfil y resultado;
- decidir con el profesor cómo se entregan las reglas semánticas;
- conservar Compiscript y MiniCalc como pruebas de generalidad.

## Daniel

Archivos:

```text
src/semantic/types.py
src/semantic/values.py
src/semantic/expression_actions.py
tests/semantic/test_types.py
tests/semantic/test_expressions.py
```

Entrega tipos primitivos, arreglos, funciones, clases, error, desconocido y
acciones genéricas para literales, operadores, asignaciones, ternario e índices.

No importa ANTLR ni usa nombres de reglas.

## Dulce

Archivos:

```text
src/antlr_mode/
src/parser/parse_tree.py
tests/antlr_mode/
```

Mantiene inspección, generación, caché, carga dinámica, diagnósticos, consumo
completo y metadatos del árbol. Revisa casos de Java/red ausentes y gramáticas
inválidas.

No modifica los algoritmos YAPar.

## Nadissa

Archivos:

```text
src/semantic/diagnostics.py
src/semantic/symbol_table.py
src/semantic/profile.py
src/semantic/evaluator.py
tests/semantic/test_symbol_table.py
tests/semantic/test_profile.py
tests/semantic/test_evaluator.py
```

Entrega scopes persistentes, símbolos, carga y validación de perfiles, registro
seguro de acciones y recorrido semántico.

No usa `eval` ni ejecuta código del perfil.

## Nelson

Archivos:

```text
src/gui/app.py
src/gui/antlr_results.py
semantic_profiles/compiscript.semantic.json
tests/semantic/test_end_to_end.py
README.md
docs/phase3/
```

Mantiene ambos modos en una ventana, presenta tokens, árboles, diagnósticos y
tabla de símbolos. Coordina el perfil de Compiscript con revisión de los otros
tres integrantes.

No reescribe la interfaz YAPar.

## Orden de integración

1. Revisar y estabilizar modo ANTLR.
2. Integrar diagnósticos, tipos y símbolos.
3. Integrar perfil y evaluador.
4. Agregar acciones semánticas por dominio.
5. Presentar resultados en GUI.
6. Probar otra gramática y regresiones de fases 1 y 2.

## Reglas de colaboración

- Un propietario principal por archivo.
- PRs pequeños con implementación y pruebas.
- Ningún generado en Git.
- Ningún nombre Compiscript dentro del motor.
- Revisión por una persona distinta.
- Contratos se cambian en PR específico.
- Cada fixture declara gramática y regla inicial.

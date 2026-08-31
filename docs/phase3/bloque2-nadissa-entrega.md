# Entrega del Bloque 2 — Nadissa Vela

## Alcance cerrado

Este bloque implementa el motor semántico genérico que recibe árboles
`ParseTreeNode` y perfiles declarativos. No importa ANTLR, Java o PyQt6, no
contiene nombres de reglas de Compiscript y no ejecuta código indicado por el
JSON. Los scopes cerrados se preservan para que los bloques posteriores puedan
presentar la tabla de símbolos.

## Archivos entregados

```text
src/semantic/symbol_table.py
src/semantic/profile.py
src/semantic/action_registry.py
src/semantic/results.py
src/semantic/evaluator.py
src/semantic/actions/__init__.py
src/semantic/actions/declarations.py
src/semantic/actions/control_flow.py
src/semantic/actions/callables.py
src/semantic/actions/classes.py
tests/semantic/test_symbol_table.py
tests/semantic/test_profile.py
tests/semantic/test_evaluator.py
tests/semantic/test_statement_actions.py
tests/semantic/test_functions.py
tests/semantic/test_control_flow.py
tests/semantic/test_classes.py
tests/semantic/test_general_semantics.py
```

No se modificaron contratos o archivos de Daniel, Dulce, Nelson, YAPar, YALex,
ANTLR o GUI.

## APIs públicas

### Símbolos

- `ScopeKind`: `GLOBAL`, `FUNCTION`, `CLASS`, `BLOCK`.
- `SymbolKind`: `VARIABLE`, `CONSTANT`, `PARAMETER`, `FUNCTION`, `CLASS`,
  `FIELD`, `METHOD`.
- `Symbol(name, kind, type, mutable, location, metadata={})` copia los
  metadatos a un mapping de solo lectura.
- `Scope.declare`, `resolve_local`, `resolve`, `symbols` y `children`.
- `SymbolTable.enter_scope`, `exit_scope`, `declare`, `resolve`,
  `iter_scopes` y `restore_global`.

`declare` devuelve `False` ante un duplicado local y nunca reemplaza el símbolo
original. `resolve` busca desde el scope actual hacia los ancestros. Salir de un
scope no lo elimina de `iter_scopes()`.

### Perfiles

- `ChildSelector(kind, index=None, token=None)`.
- `ActionInvocation(name, arguments={}, phase="exit")`.
- `RuleBinding(rule, actions, alternative=None)`.
- `SemanticProfile(name, bindings, version=1)`.
- `load_profile(path)`, `validate_profile(profile, available_rules)` y
  `resolve_binding(node, profile)`.
- `ProfileError` para configuración inválida o incompatible.

Esquema JSON versión 1:

```json
{
  "name": "perfil",
  "version": 1,
  "bindings": [
    {
      "rule": "nombreObtenidoDeLaGramatica",
      "alternative": "AlternativaOpcional",
      "actions": [
        {
          "name": "expression.literal",
          "phase": "exit",
          "arguments": {
            "kind": "integer",
            "text": {"$select": "text"}
          }
        }
      ]
    }
  ]
}
```

Los argumentos aceptan escalares JSON o uno de estos selectores:

| Selector | Resultado |
|---|---|
| `{"$select": "child", "index": 0}` | Resultado semántico de un hijo directo. |
| `{"$select": "children"}` | Resultados de todos los hijos en orden. |
| `{"$select": "token", "token": "ID"}` | Terminal directo con ese tipo. |
| `{"$select": "text"}` | Texto del nodo o concatenación de sus terminales. |
| `{"$select": "position"}` | `SourceLocation` del nodo. |

Una alternativa etiquetada tiene prioridad sobre el binding general de su
regla. Los campos desconocidos, selectores inválidos, bindings duplicados,
reglas ausentes y versiones distintas de 1 producen `ProfileError`.

### Registro y evaluador

- `ActionRegistry.register`, `resolve` y `names`.
- `SemanticContext` conserva diagnósticos, símbolos, acciones de expresiones,
  pilas contextuales, valores temporales y clases declaradas.
- `SemanticEvaluator(registry=None, source_path=None)`.
- `SemanticEvaluator.analyze(tree, profile) -> SemanticAnalysisResult`.
- `visit`, `visit_children`, `select` e `invoke` quedan disponibles para el
  adaptador del bloque 3.
- `SemanticAnalysisResult` expone `diagnostics`, `symbol_table`, `value`,
  `statistics` y `accepted`.

El recorrido ejecuta acciones `enter`, visita hijos de izquierda a derecha y
ejecuta acciones `exit`. Cada nodo restaura scopes y pilas incluso si una acción
falla. Cada llamada a `analyze` usa un contexto nuevo.

## Nombres estables de acciones

### Expresiones de Daniel

```text
expression.literal
expression.unary
expression.binary
expression.assignment
expression.ternary
expression.array
expression.index
```

### Declaraciones y scopes

```text
declare.variable
declare.constant
declare.parameter
identifier.resolve
scope.enter
scope.exit
```

### Funciones y control

```text
function.declare
function.enter
function.exit
function.call
function.return
control.condition
loop.enter
loop.exit
control.break
control.continue
control.sequence
```

### Clases

```text
class.declare
class.enter
class.exit
class.field
class.method
class.member
class.construct
class.this
```

El registro solo resuelve callables agregados por Python. Un nombre desconocido
produce `ProfileError`; el perfil no puede indicar módulos, imports o código.

## Decisiones semánticas del bloque

- El scope global se crea automáticamente y no puede cerrarse ni duplicarse.
- El shadowing se permite en hijos; la redeclaración local se rechaza.
- Una constante sin inicializador genera error `TYPE`.
- Una función se declara antes de entrar a su cuerpo, por lo que la recursión
  se resuelve léxicamente.
- Una función anidada conserva su `definition_scope` como metadato de closure.
- Argumentos y retornos usan `is_assignable` del contrato de Daniel.
- Las cinco construcciones de control exigidas usan la misma acción booleana;
  el perfil suministra su etiqueta visible.
- `break` y `continue` requieren una pila de ciclo; `return` requiere función.
- El código posterior a una transferencia definitiva genera `WARNING` general,
  que se presenta sin convertir por sí solo el resultado en rechazo.
- Los miembros se almacenan en el símbolo de clase y el acceso consulta ese
  directorio declarado.
- Invocar un constructor inexistente o con argumentos incompatibles es error.
- `this` requiere un contexto de clase activo.

No se implementaron `foreach`, `try/catch` ni reglas nuevas de herencia porque
el plan las clasifica fuera del mínimo mientras no exista confirmación oficial.

## Evidencia

Las pruebas contienen éxito y fallo localizables para:

```text
TYP-05
SCP-01 SCP-02 SCP-03 SCP-04
FUN-01 FUN-02 FUN-03 FUN-04 FUN-05
CTL-01 CTL-02 CTL-03
CLS-01 CLS-02 CLS-03
GEN-01 GEN-03
```

Además prueban JSON inválido, acción y selector desconocidos, prioridad de
alternativa, orden de recorrido, restauración tras excepción, múltiples
diagnósticos y dos perfiles con nombres de reglas diferentes usando la misma
acción.

Comandos de verificación al cerrar el bloque:

```text
py -3 -m pytest tests/semantic -q   -> 171 passed
py -3 -m pytest -q                  -> 180 passed
py -3 -m compileall -q src tests    -> OK
```

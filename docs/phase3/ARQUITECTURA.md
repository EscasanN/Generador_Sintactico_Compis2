# Arquitectura vigente de Compiscript

## Flujo completo

```text
Fuente .cps
   ↓
src/antlr_mode/runner.py
   ├── inspecciona Compiscript.g4
   ├── genera o reutiliza Lexer/Parser de ANTLR
   ├── ejecuta la regla program
   └── convierte el árbol nativo a ParseTreeNode
   ↓
src/semantic/antlr_adapter.py
   ├── valida identidad y esquema del perfil
   ├── recorre el árbol con SemanticTreeListener
   └── produce SemanticAnalysisResult
   ↓
diagnósticos + tabla de símbolos + resultado ACCEPT/REJECT
   ↓
CLI o GUI
```

## Componentes

### Frontend ANTLR

- `src/compiscript/grammar/Compiscript.g4`: sintaxis oficial.
- `src/antlr_mode/grammar_info.py`: nombre y reglas de la gramática.
- `src/antlr_mode/runner.py`: generación, caché, tokens y análisis.
- `src/antlr_mode/parse_tree.py`: representación común del árbol.
- `src/antlr_mode/parse_tree_visualizer.py`: renderizado Graphviz.

### Semántica

- `semantic_profiles/compiscript.semantic.json`: bindings declarativos.
- `src/semantic/profile.py`: carga y validación estricta del perfil.
- `src/semantic/antlr_listener.py`: puente entre eventos ANTLR y acciones.
- `src/semantic/evaluator.py`: contexto, selectores y ejecución segura.
- `src/semantic/actions/`: declaraciones, funciones, flujo y clases.
- `src/semantic/types.py`: sistema de tipos.
- `src/semantic/symbol_table.py`: ámbitos y resolución léxica.
- `src/semantic/diagnostics.py`: errores y warnings acumulables.

### Consumidores

- `src/main.py`: CLI con gramática y perfil oficiales.
- `src/gui/app.py`: editor `.cps` y ejecución en segundo plano.
- `src/gui/semantic_results.py`: diagnósticos y tabla de símbolos.
- `src/gui/parse_tree_view.py`: árbol navegable.

## Decisiones

1. La sintaxis siempre se ejecuta antes que la semántica.
2. Un error sintáctico evita recorrer un árbol inválido.
3. El perfil no ejecuta código arbitrario: solo acciones registradas.
4. El fingerprint impide combinar una gramática con un perfil incompatible.
5. Los errores se acumulan para ofrecer más de un diagnóstico por ejecución.
6. Los warnings conservan `ACCEPT`.
7. La GUI usa un hilo de trabajo para no bloquear la interfaz.

## Extensión futura

La siguiente fase, como código de tres direcciones, debe consumir el árbol y la
información semántica solamente después de un resultado aceptado. No requiere
modificar la gramática mientras la sintaxis de Compiscript permanezca igual.

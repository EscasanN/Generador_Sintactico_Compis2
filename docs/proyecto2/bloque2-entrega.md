# Bloque 2: anotaciones, símbolos y registros de activación

Entrega para el Bloque 3. No emite TAC; solo datos y APIs.

## Archivos

| Archivo | Contenido |
|---|---|
| `src/semantic/results.py` | `SemanticAnnotations` (mapas inmutables) y campo `annotations` en `SemanticAnalysisResult` (con valor por defecto). |
| `src/semantic/evaluator.py`, `antlr_listener.py` | Registran el scope activo de cada nodo tras las acciones `enter`; limpian el estado al terminar o abortar. |
| `src/semantic/actions/declarations.py` | `identifier.resolve` guarda el `Symbol` resuelto en el nodo (necesario para el destino de `x = e;`, que es un terminal sin valor). |
| `src/codegen/layout.py` | Tamaños, alineación, `StorageClass`, `SymbolLayout`, `SymbolLayoutTable`, `ClassLayout`, `LayoutBuilder`, `LabelRegistry`. |
| `src/codegen/activation.py` | `ActivationRecordLayout`, `ActivationRecordBuilder`, `EnvironmentLayout`, `CaptureAnalysis`, `build_runtime_layouts`, `RuntimeLayouts`. |
| `src/codegen/semantic_facts.py` | `SemanticFactsIndex`: implementación real del protocolo `SemanticFacts`. |

## Uso desde el pipeline

```python
run = analyze_semantics_with_g4(GRAMMAR, source, PROFILE)          # sintaxis + semántica
facts = SemanticFactsIndex.from_result(run.semantic_result, run.syntax_result.tree)
facts.layouts            # RuntimeLayouts
# ... generar IR con ExpressionLowerer(builder, facts) ...
final = facts.layouts.finalize_temporaries(program, global_peak=...)   # slots de temporales
```

Pasar el árbol (`root`) permite decidir si el entorno de una closure puede escapar;
sin él todo entorno se marca `heap` de forma conservadora.

## Contrato público

**`SemanticFactsIndex`** (consulta por identidad de `ParseTreeNode`):
`value_for`, `symbol_for`, `scope_for`, `address_for`, `member_offset`, `lexical_access`.
Un hecho ausente lanza `MissingFactError` (subclase de `LookupError`), que
`ExpressionLowerer` convierte en `IRGEN-MISSING-FACT`. Extras: `activation_for(node)`,
`label_for(symbol)`, `declaring_scope(symbol)`.

**`LexicalAccess.kind`**: `local`, `global`, `field`, `method`, `captured`.
Para `captured`, `depth` = saltos de enlace de acceso a partir del `env` recibido
(0 = el entorno que creó la función que la encierra; 1 = un salto más) y `offset` = posición en ese entorno.

**`RuntimeLayouts`**: `symbols` (`SymbolLayoutTable`), `classes` (por nombre),
`frames`, `global_frame`; `frame_for(symbol)`, `frame_by_label`, `class_layout`,
`with_temporary_peaks`, `finalize_temporaries(IRProgram)`.

## Decisiones adoptadas

- **Modelo de memoria:** el de `DISENO_TAC.md` (boolean 1, integer 4, resto 8; offsets alineados).
- **Etiquetas:** función `fn_<ruta>` (`fn_exterior.interior`), método `Clase.metodo`,
  constructor `Clase.constructor` (también el implícito), clase `Clase`. Únicas; si chocan
  se agrega `_n`.
- **Nivel léxico:** número de funciones que encierran la declaración (programa = 0). El frame
  de una función tiene el nivel de su propio scope.
- **Frame:** header (`return_address`, `control_link`, `access_link`, `return_value`, 8 bytes c/u) →
  parámetros ocultos (`this`, luego `env`) → parámetros → locales → temporales (`t0…`, 8 bytes c/u).
  Locales de bloques internos no reutilizan slots (el shadowing siempre da offsets distintos).
- **Globales:** variables del programa y de bloques fuera de funciones viven en el área estática.
- **Capturas:** una variable usada desde una función interna conserva su slot en el frame del dueño
  (`storage=captured` para locales; los parámetros siguen siendo `parameter`) y tiene además
  `env_offset` en el `EnvironmentLayout` del dueño (slots desde 0; el enlace al entorno padre va
  al final). La copia al entorno (`ENV_SET`) es responsabilidad del generador. Funciones, métodos
  y clases se enlazan por etiqueta, por lo que la recursión no es una captura.
- **`needs_env`:** toda función en la cadena entre el uso y el dueño recibe `env`, aunque no use la variable.
- **HEAP_ENV:** el entorno es `heap` si alguna función de la cadena se usa como valor
  (asignada, retornada o pasada) y no solo llamada directamente.
- **Objetos:** campos heredados primero; tamaño mínimo 8 aunque la clase no tenga campos.
- **Temporales:** el pico de `IRProcedure.temporary_peak` define los slots; menos slots que el pico falla.

## Pruebas

```powershell
python -m pytest tests/semantic/test_codegen_annotations.py tests/codegen/test_semantic_facts.py tests/codegen/test_layout.py tests/codegen/test_activation.py -q
python -m pytest tests -q        # 530 pasan
```

Casos de la matriz: EXP-05, FUN-02, FUN-08, FUN-09, CLS-01, CLS-06, TMP-05,
SYM-01…SYM-06, RUN-01…RUN-04.

## Puerta Nadissa → Dulce

- [x] Regresiones semánticas completas pasan.
- [x] Un programa real produce anotaciones consultables.
- [x] `SymbolLayoutTable` contiene todos los símbolos relevantes.
- [x] `ActivationRecordLayout` valida alineación y no solapamiento.
- [x] `SemanticFactsIndex` satisface el protocolo de Daniel (probado con `ExpressionLowerer`).
- [x] No se emitieron sentencias TAC.

## Limitaciones conocidas

- La variable capturada se copia al entorno (semántica por valor, como en `DISENO_TAC.md`);
  mutaciones posteriores desde la closure no se reflejan en el dueño.
- Los slots de temporales miden 8 bytes sin importar su tipo.
- Los temporales del código global se reservan en `global_frame` con `global_peak`.

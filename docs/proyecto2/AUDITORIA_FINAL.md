# Auditoría y cierre final de Proyecto 2

## Base y autoría

El cierre autorizado por Daniel Chet parte de `4db56b8`, entrega publicada del
Bloque 4 que contiene los cuatro bloques. La rama de correcciones es
`fix/proyecto2-final-compliance`; la integración de entrega es
`feature/proyecto2-codegen`. Se conservan todos los commits individuales de
Daniel, Nadissa, Dulce y Nelson. Los parches posteriores son de Daniel.

La línea base se reprodujo con **790 pruebas aprobadas**. La auditoría encontró
contraejemplos fuera de esa cobertura; cada corrección comenzó con una prueba
fallida del comportamiento real. No se modificaron la gramática, su fingerprint,
el perfil semántico ni los módulos semánticos.

## Hallazgos corregidos y evidencia

| Hallazgo | Corrección | Evidencia principal |
|---|---|---|
| Colisión de nombres `t0`/`t1` | Slots de temporales únicos, conservando capacidad del pico e identidad del símbolo | `test_user_temporary_names_never_collide_with_frame_slots`, fixture `TMP-05-identificadores-temporales.cps` |
| Clases homónimas sobrescritas | Layouts por identidad y colección por etiquetas únicas; consulta textual ambigua rechazada | `test_shadowed_classes_keep_distinct_symbols_fields_and_constructors` |
| Closure hermana sin entorno | Propagación de dependencias hasta punto fijo | `test_sibling_function_dependencies_propagate_environments`, `FUN-07-closures-hermanas.cps` |
| Clase local sin entorno en métodos/constructores | Instancia retiene entorno; ocultos ordenados `this`, `env`, parámetros; scopes internos para constructores implícitos | `test_local_class_captures_are_carried_by_the_instance`, `CLS-04-clase-local-capturada.cps` |
| `this` anidado y miembros implícitos | Receptor capturado según el símbolo resuelto, incluidas escrituras y otras clases anidadas | `test_nested_functions_capture_the_method_receiver`, `test_nested_class_uses_the_receiver_of_the_resolved_outer_member` |
| Método ligado pierde entorno | `IRProcedure.bound_environment_offset` y encabezado `[bound_env=N]`; `METHOD_REF` liga receptor y entorno | `test_bound_method_values_record_the_retained_environment_in_the_ir` |
| Campo heredado inicializado en slot incorrecto | Offset del símbolo declarado y contexto estático del inicializador | `test_inherited_field_initializers_keep_the_declaring_symbol_offset`, `test_inherited_initializer_calls_keep_the_static_declaration_context` |
| Ternario mixto sin promoción | Conversión dentro de cada rama, antes de la unión | `test_mixed_ternary_converts_integer_branch_before_the_join` |
| IR inválida aceptada | Firma de destinos conocidos, accesos a frames y descriptor de método comprobados | `test_call_arity_is_checked_against_the_known_procedure`, `test_verifier_rejects_foreign_frame_reads`, `test_verifier_requires_this_then_env_for_bound_methods` |
| Retorno no void faltante | Diagnóstico `IRGEN-MISSING-RETURN` sin TAC | `test_control_completion.py`, `FUN-04-retorno-faltante.cps` |
| Manejadores activos después de salir de try | Retirada según profundidad abandonada y ruta excepcional en el verificador | `test_control_completion.py`, `EXT-07-salidas-try.cps` |
| Resultado del worker asociado a otro documento | Revisión de documento, invalidación al editar/abrir/guardar como y descarte de respuesta obsoleta | `test_document_changes_discard_a_running_workers_obsolete_result` |
| Exportación rechazada con archivo previo | Se preserva el archivo y se advierte que no fue actualizado | `test_rejected_export_preserves_and_identifies_an_existing_tac_file` |

Las pruebas de codegen anteriores están en `tests/codegen/test_final_compliance.py`
salvo las indicadas por módulo. Las del IDE están en
`tests/gui/test_codegen_results.py`; la de CLI, en `tests/test_main_cli.py`.
Los fixtures están en `tests/cps/codegen`. La captura de `this` que antes se
presentaba como caso inválido ahora es un fixture positivo.

## Decisiones y límites

- Daniel eligió rechazar salidas alcanzables sin valor en funciones no `void`.
  Es una validación de codegen; no se atribuye esta decisión al profesor.
- El análisis de salida contempla el CFG emitido y booleanos inmediatos; no es
  un demostrador general de terminación. Se aceptan bucles sin salida probada
  y se conservan retornos implícitos para `void` y constructores.
- Capturas por referencia a entornos compartidos. Los entornos retenidos en
  instancias pueden sobrevivir al frame y se marcan de heap conservadoramente.
- `METHOD_REF` usa el descriptor del procedimiento para ligar `this` y `env`;
  `CLOSURE_CALL` cuenta solo argumentos explícitos.
- El manejo de excepciones sigue siendo IR abstracta. `CATCH` consume el
  manejador disparado; las transferencias normales usan `TRY_END`.
- Se conserva resolución estática de métodos, `switch` booleano con caída y
  `break`/`continue` asociados a bucles, según el frontend vigente.
- `Clase.campo` estático sigue rechazado: el lenguaje no declara miembros
  estáticos. Tampoco se añaden vtables, GC, optimización global ni backend nativo.
- Una exportación fallida preserva archivos previos; el estado actual debe
  consultarse mediante el código de salida y los diagnósticos, no solo por la
  existencia de un archivo `.tac`.
- Limitación semántica preexistente, fuera de estos parches: herencia entre
  clases declaradas dentro de una función puede perder la superclase. Se
  reprodujo `function f():integer { class A { let x:integer=1; } class B:A {}
  let b=new B(); return b.x; }` y el frontend rechaza `class 'B' has no member
  'x'`. La herencia global sigue cubierta. Resolver esta combinación requiere
  trabajo posterior sobre el frontend, que este plan conserva intacto; no se
  presenta como un requisito de combinaciones semánticas cerrado al 100 %.

## Validación y demostración

Ejecutado el 2026-10-17, Python 3.14.7, con los siguientes resultados:

| Comando | Resultado |
|---|---:|
| `python -m pytest tests/codegen -q` | 422 passed |
| `python -m pytest tests/semantic -q` | 371 passed |
| `python -m pytest tests/antlr_mode -q` | 12 passed |
| `python -m pytest tests/gui -q` | 31 passed |
| `python -m pytest tests/test_main_cli.py -q` | 16 passed |
| `python -m pytest tests -q` | 852 passed en 28.49 s |
| `git diff --check` | Sin errores |
| `python -m compileall -q src/codegen src/gui src/main.py` | Sin errores |

Revisión independiente de `4db56b8` al código de `035b50b`: **ready to merge**,
sin hallazgos críticos, importantes ni menores de código pendientes. Sus
observaciones sobre escrituras implícitas, receptores de miembros externos y
prefijo real de parámetros ocultos quedaron reproducidas y corregidas.

Commits de implementación de Daniel:

- `6ec2992`: identidades, slots y entornos de closures/clases.
- `2f3e11b`: retornos, transferencias, métodos ligados y verificación reforzada.
- `035b50b`: revisión de documento del IDE y exportación rechazada de la CLI.

Comandos de aceptación:

```powershell
python -m pytest tests/codegen -q
python -m pytest tests/semantic -q
python -m pytest tests/antlr_mode -q
python -m pytest tests/gui -q
python -m pytest tests/test_main_cli.py -q
python -m pytest tests -q
git diff --check
```

La copia creada con `git archive 035b50b`, sin archivos generados previos, pasó
la suite completa: **852 passed en 36.38 s**. El frontend regeneró sus artefactos
fuera del checkout de trabajo. Los cambios documentales posteriores no cambian
ese código ni sus pruebas.

También se verificaron los códigos de salida de la CLI: demo completo, clase
local capturada y closures hermanas terminan en 0; retorno faltante termina en
1, informa `IRGEN-MISSING-RETURN` y deja stdout sin TAC.

Para presentar:

1. Abrir `DEMO-completa.cps` en el IDE; mostrar TAC, procedimientos, tabla
   extendida y registros de activación.
2. Mostrar `FUN-07-closures-hermanas.cps` y explicar cómo una función sin
   lecturas directas también recibe el entorno que necesita su hermana.
3. Compilar `CLS-04-clase-local-capturada.cps`: entorno en instancia, método
   ligado guardado globalmente y descriptor `[bound_env=N]`.
4. Mostrar el slot de usuario y los temporales en
   `TMP-05-identificadores-temporales.cps`.
5. Compilar `FUN-04-retorno-faltante.cps`; mostrar código y ubicación del
   diagnóstico sin TAC. Volver al demo válido y luego al fallido.
6. Editar o abrir otro documento durante una compilación: ningún resultado
   anterior debe presentarse como vigente ni permitir exportación.
7. Repetir el demo por CLI con `--emit-tac` y las capturas con `--show-layout`.

Los pasos de IDE usan `tests/cps/codegen/validos`, salvo los casos rechazados,
que están en `invalidos`. Las pruebas Qt se ejecutan en modo offscreen; el ensayo
visible y la defensa ante los calificadores corresponden al equipo.

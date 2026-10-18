# Auditoría y cierre final de Proyecto 2

## Base y autoría

El cierre autorizado por Daniel Chet parte de `4db56b8`, entrega publicada del
Bloque 4 que contiene los cuatro bloques. La rama de correcciones es
`fix/proyecto2-final-compliance`; la integración de entrega es
`feature/proyecto2-codegen`. Se conservan todos los commits individuales de
Daniel, Nadissa, Dulce y Nelson. Los parches posteriores son de Daniel.

La línea base se reprodujo con **790 pruebas aprobadas**. La auditoría encontró
contraejemplos fuera de esa cobertura; cada corrección comenzó con una prueba
fallida del comportamiento real. En ese primer cierre no se modificaron la
gramática, su fingerprint, el perfil semántico ni los módulos semánticos. La
corrección posterior de herencia local, autorizada por Daniel, se detalla abajo.

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
| Herencia local pierde superclase o capturas | Perfil transmite la base; resolución por identidad y entorno de cada clase base durante inicialización | `test_local_inheritance.py`, `test_cls_04_success_local_subclass_preserves_inherited_members`, `CLS-06-herencia-local.cps` |

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
- La limitación de herencia local señalada en el primer cierre quedó corregida
  en el parche posterior descrito abajo. Una suite aprobada no demuestra la
  ausencia de todo posible defecto ni sustituye el ensayo de presentación.

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

El merge local de integración `3547db8` volvió a pasar la suite completa:
**852 passed en 29.96 s**. El cierre posterior únicamente normaliza dos finales
de archivo heredados y registra este resultado; no cambia lógica ni pruebas.

### Corrección posterior: herencia local

Daniel autorizó corregir el defecto semántico pendiente el 2026-10-17. La rama
`fix/proyecto2-local-inheritance` parte de `b53bd44`, sin cambios ajenos en el
workspace. Esta ampliación modifica de forma acotada tres módulos semánticos,
el perfil de Compiscript y la integración de capturas/inicializadores en codegen;
no modifica la gramática ni su fingerprint, la GUI ni la CLI.

La causa original era que `ClassWithSuper` no suministraba la superclase a la
acción de declaración. Las clases globales ocultaban el defecto gracias a la
predeclaración del programa. Ahora `class.declare_from_tree` recibe el nombre
de token desde el perfil y transmite el segundo identificador a `class.declare`,
sin introducir nombres de reglas de Compiscript en el motor genérico.

También quedaron protegidos los casos relacionados:

- Miembros heredados se buscan por identidad del tipo declarado, no en la
  última clase homónima visitada; las anotaciones de tipo usan el ámbito léxico.
- Cada inicializador heredado usa el entorno retenido por su propia clase base,
  aunque el constructor ejecutado sea el de una subclase de otro ámbito.
- La construcción de una subclase propaga las dependencias de entorno de todos
  sus ancestros, incluso desde funciones más anidadas.
- Superclases inexistentes o que no son clases siguen rechazadas; miembros
  inexistentes detienen el pipeline semántico sin producir TAC.

Las regresiones se observaron fallar antes de corregir el código. Verificación
del parche, el 2026-10-17:

| Comando | Resultado |
|---|---:|
| `python -m pytest tests/codegen -q` | 431 passed en 7.64 s |
| `python -m pytest tests/semantic -q` | 377 passed en 4.04 s |
| `python -m pytest tests -q` | 867 passed en 30.10 s |
| `git diff --check` | Sin errores |
| `python -m compileall -q src/semantic src/codegen` | Sin errores |

Una copia de `git archive 2ae29b7`, sin artefactos generados del workspace,
también pasó **867 pruebas en 38.91 s**. La CLI aceptó el fixture nuevo con
`--emit-tac`: 51 instrucciones y 6 procedimientos, con pico de 3 temporales.

Se solicitó revisión independiente del rango `b53bd44..2ae29b7`, pero el agente
de revisión no pudo ejecutarse por el límite de gasto del workspace. **Ese
intento inicial no produjo dictamen independiente.** Como alternativa se revisó
localmente el diff completo: registro de acciones, identidad de tipos, ámbitos,
propagación de entornos, restauración del contexto mediante `finally`, últimos
consumos de temporales y ubicaciones de instrucciones. También se comprobaron
inicializadores con `this`, llamada a método, escritura de captura y método
heredado ligado que escapa del creador. No se detectaron bloqueos en ese alcance;
no se amplió el trabajo a rediseñar tipos nominales ni visibilidad de
declaraciones locales adelantadas, ni a ejecutar TAC en un backend nativo.

El fixture adicional es `tests/cps/codegen/validos/CLS-06-herencia-local.cps`:
base y subclase locales, entornos de funciones distintas, construcción en una
tercera función y llamada a método heredado. Su resultado es TAC verificado;
no se afirma ejecución nativa, que no es el backend de este proyecto.

### Cierre posterior: nominalidad y seguridad del documento

El reintento de revisión independiente sí se completó con tres subagentes sobre
`bf989e3`. El mínimo documental/funcional del enunciado cuenta con evidencia,
pero la revisión y el ensayo encontraron dos problemas importantes y uno menor:
compatibilidad incorrecta entre clases homónimas, pérdida de cambios sin guardar
al pulsar Programa y salto a Semántica al cambiar el tema. Daniel autorizó
corregirlos en `fix/proyecto2-types-and-ide`, desde ese commit y sin cambios ajenos.

Correcciones verificadas mediante TDD:

- `ClassType` representa una declaración nominal inmutable. Cada declaración
  crea una instancia distinta; referencias y ancestros conservan ese objeto.
  Igualdad y hash por identidad impiden mezclar homónimos en asignaciones,
  argumentos, retornos, arreglos y firmas de función. Primitivos y estructuras
  compuestas conservan sus reglas; herencia real y `null` siguen aceptados.
- La fila Programa da foco al editor y no recarga desde disco. Abrir, Nuevo y
  cerrar ofrecen Guardar / Descartar / Cancelar. Una cancelación o error al
  guardar conserva el documento; guardar en la misma ruta no invalida su TAC.
- Nuevo no vacía el archivo que acaba de guardar el aviso de cambios, incluso
  si las rutas coinciden por sufijo, normalización o hardlink. Se conserva el
  programa guardado y se solicita otro nombre para el nuevo.
- Cambiar tema no reconstruye el bundle: conserva pestaña, búsquedas,
  selecciones y expansiones. Solo recolorea el resumen y conserva su selección
  y scroll; el encabezado de error interno mantiene el color de error.

Evidencia versionada: `tests/semantic/test_nominal_classes.py`,
`tests/gui/test_document_safety.py` y
`tests/cps/codegen/invalidos/PIPE-02-clases-homonimas.cps`. Las dos expectativas
anteriores que construían otra clase del mismo nombre ahora comprueban la
declaración canónica real. El inventario es **22 válidos, 11 inválidos y 7 golden**.

Verificación del código hasta `379f59f`, el 2026-10-17:

| Comando / recorrido | Resultado |
|---|---:|
| `python -m pytest tests/semantic -q` | 389 passed |
| `python -m pytest tests/codegen -q` | 433 passed |
| `python -m pytest tests/gui -q` | 55 passed en 21.92 s |
| `python -m pytest tests -q` | 905 passed en 33.98 s |
| Ensayo del IDE con ventana Windows y diálogos Qt reales | 72 / 72 comprobaciones aprobadas |
| `git diff --check`, `compileall` de semántica/GUI | Sin errores |

El ensayo fue automatizado mediante eventos de Qt, no una interacción humana.
Probó demo completo, closures, herencia local, temporales, errores por fase,
exportación UTF-8/LF, tablas/frames, rutas con acentos, válido → inválido → válido,
descarte de workers obsoletos y decisiones reales de guardado/cancelación.
Se inspeccionaron capturas de ambas paletas y de los avisos. La evidencia local
queda en `output/qa/ensayo-proyecto2-20261017-corregido/` (ignorada por Git).

Dos revisiones independientes del parche dieron **Ready to merge: Yes**:
nominalidad (`bf989e3..cb3d4a3`) y documento/tema (`bf989e3..379f59f`). Los
hallazgos de colisiones de rutas se reprodujeron con pruebas fallidas antes de
corregirlos. No quedan bloqueos identificados dentro de estos tres arreglos.
Mejora cosmética opcional: los diagnósticos entre homónimos pueden mostrar el
mismo nombre textual en ambos lados, aunque el rechazo nominal es correcto.
El cierre con worker activo conserva su comportamiento previo; no se atribuye
a este parche cancelación ni espera del hilo. La defensa oral y la comprobación
del entorno el día de la presentación siguen correspondiendo al equipo.

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
8. Compilar `CLS-06-herencia-local.cps` y mostrar los slots de entorno separados
   de la clase base y la subclase, así como la llamada al método heredado.

Los pasos de IDE usan `tests/cps/codegen/validos`, salvo los casos rechazados,
que están en `invalidos`. La suite Qt usa modo offscreen; el ensayo adicional
anterior usó ventana Windows visible. El equipo debe repetir la demostración
en el entorno de evaluación y preparar su defensa ante los calificadores.

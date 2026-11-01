# Registro de validación

Se desarrolló con pruebas previas por bloques: frontend, AST, almacenamiento, semántica/ejecución e integración GUI/CLI. Las primeras ejecuciones mostraron capacidades ausentes; se agregó el código, se verificó y se ampliaron regresiones. Casos nuevos detectaron y corrigieron recuperación de candidatos AND, igualdad numérica en índices, literales negativos, nombres de tokens y equivalencia de nombres agrupados.

Entorno observado: Windows, Python 3.14.7, Java 21 para generación ANTLR 4.13.2; ANTLR runtime, pytest y PyQt6 disponibles en Python del sistema. El entorno virtual de Compiscript era inaccesible y no se utilizó.

Comando reproducible de suite completa: `py -m pytest -q`. El fixture configura temporales bajo `tmp/` por restricciones de acceso al temporal global de Windows. Pruebas GUI con Qt offscreen; no requieren servidor gráfico.

Las pruebas verifican valores esperados manuales, operaciones sobre almacenamiento real y reabertura, sin DBMS. Las pruebas de índice prohíben recorrido completo para consultas compatibles, cuentan lecturas y prueban actualizaciones y borrados. El fallo simulado de publicación verifica que la generación vigente no cambia. Se verifica que analizar no abra archivos de escritura y no cree un almacenamiento ausente.

## Validación inicial (antes de la auditoría)

* Suite completa: **98 passed**, `py -m pytest -q`, 8.05 s en la ejecución final del código.
* Revisión independiente: verificó inicialmente 64 pruebas, reprodujo casos adicionales de índices, literales, agrupación y desbordamiento. Se agregaron regresiones fallidas y se corrigieron. La revisión final enfocada no encontró problemas materiales pendientes.
* Wheel construido sin dependencias ni aislamiento de build: `py -m pip wheel --no-deps --no-build-isolation --wheel-dir tmp/wheels .`.
* Wheel instalado en un directorio aislado mediante `scripts/verify_install.py`; procesos nuevos ejecutaron demo, reabrieron almacenamiento y ejecutaron consultas. PYTHONPATH apuntó exclusivamente al paquete instalado, sin referencia a `src` ni a Compiscript.
* Proceso con `-B` y audit hook sobre `open` comprobó análisis sin aperturas de escritura. La creación de base solo ocurrió durante ejecución explícita.
* Inspección visual de la GUI con demo ejecutado: editor y tabla final mostraron Ana/21 y María/22; pestañas de tokens, árbol, AST, errores y resultados disponibles. Capturas locales de QA bajo `tmp/`. Qt offscreen no enumeraba fuentes en este sandbox; se cargaron fuentes Windows en el script de captura para inspeccionar el texto. Esto no agregó dependencias al producto.
* Estado Git de Compiscript al cerrar: mismo único archivo modificado preexistente `tests/cps/codegen/validos/LST-01-listas.cps`. No se modificó ese repositorio, no se inicializó Git en el nuevo y no se hicieron commits, push ni merge.

La auditoría posterior encontró casos que esa suite no cubría: lectura de datos dañados, proyección de EXISTS, guardado no atómico del editor, copias completas por modificación e inconsistencia de subconsultas en ON. La revisión inicial no constituyó una garantía de ausencia de errores.

## Correcciones posteriores a la auditoría

Se agregaron regresiones en `tests/test_audit_fixes.py` y se observaron los fallos antes de corregirlos:

* Lecturas con JSON inválido, filas con estructura o tipo incorrecto, índices corruptos y archivos ausentes devuelven STORAGE con ruta y ubicación SQL. La revisión encontró además referencias de catálogo con tipos inválidos y RID duplicados, omitidos o con claves incompatibles; también se reprodujeron y corrigieron. La comprobación del índice usa metadatos sin leer todas las filas.
* EXISTS/NOT EXISTS no evalúan proyección ni ORDER BY; conservan WHERE, GROUP BY, HAVING y cardinalidad de agregaciones sobre entrada vacía. Se comprueba que los errores reales de filtros no se oculten.
* Guardar y Guardar como escriben en un temporal y reemplazan al terminar. Se simulan escritura parcial y reemplazo fallido: archivo anterior, texto modificado y ruta se conservan; no quedan temporales en esos casos.
* Formato 2 comparte filas e índices inmutables. El UPDATE indexado de una fila sin UNIQUE lee una fila, escribe un archivo de fila y no llama a scan; se comprueba también el número de archivos escritos y la conservación de originales. Las tablas ajenas no se leen ni copian.
* Persistencia desde formato 1 verificada con fixture independiente: consulta indexada, modificación, reapertura en formato 2 y conservación de la vista antigua. Fallos al publicar una actualización incremental preservan datos e índices anteriores.
* UNIQUE se valida en el estado final de la tabla afectada; se verifican violaciones atómicas y swaps simultáneos válidos.

Resultado posterior a las correcciones: **130 passed**, `py -m pytest -q`, 10.54 s. La revisión independiente enfocada confirmó el cierre de los hallazgos sin nuevos problemas en los cambios revisados. Se reconstruyó el wheel y se repitió `scripts/verify_install.py` con éxito para instalación aislada, CLI, reapertura y análisis sin escrituras.

Límites operativos: un escritor simultáneo, generaciones retenidas sin compactación, subconsultas exclusivamente en WHERE, claves/índices simples y pruebas gráficas offscreen. Se reescriben los metadatos y cada índice afectado como archivo completo; UNIQUE puede requerir recorrer su tabla. No se promete concurrencia entre procesos ni recuperación ante corte eléctrico.

## Correcciones de índices y prevalidación de subconsultas

Se agregaron `tests/test_subquery_planning.py`: primero se observaron nueve fallos para operandos con signo invertidos, índices exteriores en IN/NOT IN y escalares, repetición de subconsultas independientes y ausencia de prevalidación. Se implementó detección de correlación con ámbitos anidados, caché por sentencia, selección indexada de candidatos y prevalidación de cardinalidad de solo lectura. La revisión independiente detectó un caso adicional con alias en ORDER BY; se reprodujo mediante una prueba fallida y se corrigió. La revisión independiente se interrumpió después por el límite de uso del servicio y no emitió un dictamen final para este bloque.

La suite completa posterior pasó **144 pruebas**, `py -m pytest -q`, 23.25 s. Incluye NULL, conjuntos vacíos, duplicados, correlación y ausencia de reutilización de resultados tras modificar datos. Las pruebas de planes impiden scan sobre la tabla exterior y comprueban que una subconsulta independiente se lea una sola vez. La prevalidación detecta cardinalidad inválida incluso con una tabla exterior vacía para subconsultas independientes, y detiene UPDATE antes de aplicar cambios.

Wheel reconstruido e instalado de forma aislada con éxito. `scripts/verify_install.py` comprueba además análisis con datos sin escrituras y comparación invertida con signo usando índice en el paquete instalado. El análisis de scripts después de su primera modificación sigue siendo estático; cada sentencia ejecutada recibe prevalidación con el estado vigente. Las subconsultas correlacionadas se validan en los contextos exteriores existentes y conservan evaluación por contexto.

# Arquitectura y archivos

## Separación

* `frontend`: ANTLR y árbol sintáctico neutral, tokens y diagnósticos. Importa módulos generados, nunca genera ni ejecuta procesos.
* `ast`: conversión a Script, Command, Select, Expr, ColumnDef, TableRef y SelectItem; no conserva dependencias a los nodos ANTLR.
* `semantic`: catálogo, ámbitos, resolución de alias/columnas, tipos, restricciones estáticas y reglas de agregación. No accede al almacenamiento.
* `interpreter`: evaluación de expresiones, consultas, agrupación, subconsultas y cambios preparados en memoria.
* `storage` e `indexes`: persistencia y acceso por RID; no interpretan SQL.
* `api`: analiza o ejecuta y devuelve diagnósticos. `cli` y `gui` comparten esta API.

La ejecución comprueba la cardinalidad escalar en una prevalidación de solo lectura antes de aplicar la sentencia, y vuelve a protegerla al evaluar expresiones. `analyze_sql(..., storage=store)` también realiza esa comprobación sobre datos existentes; CLI y GUI proporcionan ese almacenamiento. Sin `storage`, solo se validan estructura y tipos. En scripts analizados, la comprobación dinámica cubre las consultas anteriores a la primera sentencia modificadora: las posteriores solo se validan estáticamente porque el análisis no aplica cambios. Al ejecutar, cada sentencia se prevalidará con el estado producido por las anteriores. Las correlacionadas se comprueban en los contextos exteriores disponibles; con cero filas exteriores no se inventan contextos. Las ubicaciones públicas son desde 1 y los intervalos de token tienen extremo final exclusivo.

Las subconsultas no correlacionadas se reutilizan por instancia de intérprete y sentencia. Se consideran ámbitos anidados y alias de ORDER BY para detectar dependencias exteriores. Los resultados nunca se reutilizan entre sentencias ni para subconsultas correlacionadas. IN/NOT IN no correlacionados y comparaciones escalares independientes permiten obtener candidatos mediante el índice de la columna exterior; se conserva la lógica de NULL y conjuntos vacíos. Los literales con signo pueden aparecer en cualquier lado de la comparación.

## Formato versión 2 y compatibilidad

```text
database/
  manifest.json                         # {format:2,generation:"..."}
  generations/<uuid>/
    catalog.json                        # tablas, columnas, tipos, restricciones, índices
    rows.json                           # tabla -> {RID: generación propietaria}
    indexes.json                        # índice -> generación propietaria
    tables/<tabla>/<RID>.json            # solo filas insertadas o modificadas
    indexes/<índice>.json                # clave tipada -> lista de RID
```

Todos son archivos JSON UTF-8. Fechas se guardan como ISO; NULL como null. El esquema distingue DATE de VARCHAR y BOOLEAN de INT. Las claves numéricas del índice normalizan igualdad INT/FLOAT sin convertir grandes enteros a float.

El lector también admite el formato 1 anterior: `rows.json` contenía listas de RID y todos los archivos pertenecían a la generación vigente. Abrir o analizar una base antigua no escribe ni migra archivos. La siguiente modificación explícita publica formato 2 y conserva referencias a sus archivos anteriores. Las generaciones antiguas no se deben eliminar manualmente: pueden contener filas o índices referenciados por la base vigente.

Las lecturas usan una generación inmutable. Un lookup carga el archivo del índice, encuentra RIDs y abre únicamente sus archivos de fila; no escanea filas para localizar coincidencias. Abrir el catálogo carga la lista de RIDs como metadatos, no los valores de cada fila. Índices grandes se examinan en memoria para rangos: no se promete un árbol B ni complejidad logarítmica.

INSERT/UPDATE/DELETE preparan un conjunto de cambios `RID -> fila nueva/None`. UPDATE/DELETE recuperan candidatos mediante índice cuando es compatible. Solo las filas nuevas o modificadas se escriben; los borrados eliminan referencias. Las filas y los índices de tablas ajenas se reutilizan. La unicidad se comprueba sobre el estado final de la tabla afectada cuando se inserta o cambia una columna UNIQUE/PRIMARY KEY: puede requerir leer esa tabla, sin recorrer tablas ajenas.

`commit_changes(catalog, changes)` publica estos cambios; `commit(catalog, tables)` conserva el contrato de reemplazo completo para clientes anteriores. Cada índice afectado se actualiza a partir de los RID cambiados y se escribe completo como archivo JSON; CREATE INDEX recorre únicamente su tabla. DROP TABLE elimina las referencias a la tabla y sus índices. Se siguen reescribiendo metadatos de referencias completos, por lo que no se promete costo constante por modificación.

El almacenamiento escribe una nueva generación y un manifiesto temporal, fuerza los archivos y publica con `os.replace`. Si falla antes de publicar, el manifiesto anterior permanece. Pueden quedar generaciones huérfanas en fallos de E/S; no se usan. Las generaciones antiguas se retienen deliberadamente. No editar archivos de la base manualmente.

## Observabilidad

Cada sentencia reporta `row_reads`, `table_scans`, `index_lookups`, `row_writes` e `index_writes`. Las pruebas prohíben `scan` para consultas indexadas y para un UPDATE indexado sin restricciones UNIQUE; comprueban lecturas, archivos nuevos, conservación de archivos anteriores y resultados después de reabrir. Los fallos de publicación no alteran el manifiesto vigente.

Los errores de lectura JSON, de codificación, de archivos ausentes y de estructura detectada se convierten en diagnósticos STORAGE con la ruta afectada; la API agrega la ubicación de la sentencia SQL. No se intenta reparar datos ni reemplazar silenciosamente índices corruptos por recorridos completos.

EXISTS/NOT EXISTS comprueban si existe un lote que sobreviva a WHERE, agrupación y HAVING; no evalúan expresiones de proyección ni ORDER BY. Las subconsultas en ON se rechazan conforme al dialecto documentado.

El worker gráfico recibe una copia del SQL y su revisión. Si cambia el documento, no presenta resultados como pertenecientes al nuevo texto. Solo hay una operación pendiente por ventana; una ejecución ya iniciada puede completar sus cambios aunque el usuario edite el texto mientras tanto.

El guardado de documentos escribe un temporal junto al destino, fuerza su contenido y publica con `os.replace`. Ante fallo conserva el archivo original, el búfer modificado y la ruta anterior de Guardar como; el temporal se limpia.

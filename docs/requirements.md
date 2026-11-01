# Matriz requisito → implementación → prueba → ejemplo

Las ocho entregas se utilizaron como secuencia interna. Todos los subsistemas forman parte del proyecto final.

| Entrega / requisito | Implementación | Prueba reproducible | Ejemplo |
|---|---|---|---|
| 1 Lexer/parser propios | SQL.g4 + frontend | test_frontend: válidos/ inválidos por construcción, EOF, tokens y posiciones | `SELECT nombre FROM estudiantes WHERE edad>=18;` |
| 2 AST explícito | ast | test_ast: precedencia, subconsulta, restricciones | `SELECT a+2*3 AS n FROM t;` |
| 3 Catálogo/tipos/alias/errores | semantic + models | test_semantic y casos inválidos de test_engine | `SELECT id FROM t a INNER JOIN t b ON a.id=b.id;` falla por ambigüedad |
| 4 Tipos persistentes/CREATE/DROP/INSERT | interpreter + storage | test_ddl_insert_reopen_and_projection | `CREATE TABLE t(id INT PRIMARY KEY); INSERT INTO t VALUES(1);` |
| Restricciones/validación sin cambios parciales | semantic + validación del estado preparado | test_invalid_statements_do_not_change_files, test_update_validation_is_atomic_for_all_rows | `UPDATE t SET id=9;` falla si viola UNIQUE |
| INT/FLOAT/VARCHAR/BOOLEAN/DATE | semantic.validate_value | test_invalid_dates_and_no_implicit_text_cast, test_ddl_insert_reopen_and_projection | `DATE '2024-02-29'` válido; `DATE '2023-02-29'` inválido |
| 5 SELECT/WHERE/AND/OR/ORDER/UPDATE/DELETE | interpreter | test_dml_order_and_null_logic | `SELECT id FROM t WHERE id>1 ORDER BY id DESC;` |
| 6 INNER JOIN/agregados/GROUP/HAVING | semantic + interpreter.select | test_join_group_and_aggregates, test_group_qualified_column_and_order_alias | `SELECT aid,AVG(v) FROM b GROUP BY aid HAVING COUNT(*)>1;` |
| 7 CREATE/DROP INDEX, persistencia, acceso directo | indexes + storage.lookup/fetch | test_index_real_direct_reads_and_maintenance (scan prohibido y contadores físicos) | `CREATE INDEX ix ON t(id); SELECT * FROM t WHERE id=2;` |
| Índices con AND, números, negativos, rangos | interpreter.index_candidate | test_index_conjunction_and_numeric_equivalence, test_negative_where_uses_index | `SELECT id FROM t WHERE id=-1 AND f>0;` |
| Índices con comparación invertida y subconsultas independientes | planning + interpreter | test_subquery_planning: scan exterior prohibido, reutilización por sentencia, NULL y conjuntos vacíos | `SELECT id FROM t WHERE -1=id OR id IN (SELECT id FROM choices);` |
| Cardinalidad antes de aplicar sentencias | interpreter.preflight + api | test_dynamic_analysis_is_read_only_and_checks_even_empty_outer, test_preflight_prevents_update_before_invalid_scalar | Analizar con storage rechaza una escalar de dos filas sin escribir |
| IN/NOT IN/EXISTS/NOT EXISTS/correlación/escalares | ast + semantic + interpreter | test_subqueries_correlated_and_scalar_cardinality | `SELECT id FROM a WHERE EXISTS(SELECT * FROM b WHERE b.id=a.id);` |
| Persistencia y publicación ante fallo | storage | test_storage: reapertura, fetch directo, fallo de publicación | Reabrir FileStorage y consultar datos anteriores |
| Datos dañados con diagnóstico | storage + api | test_audit_fixes: JSON dañado, estructura de fila incorrecta, índice corrupto y fila ausente | SELECT sobre fila dañada devuelve STORAGE y ruta |
| Escrituras incrementales y compatibilidad | storage.commit_changes | test_audit_fixes: UPDATE de una fila sin scan, migración formato 1 y fallo de publicación incremental | UPDATE indexado lee/escribe una fila sin copiar tablas ajenas |
| EXISTS sin evaluar proyección | interpreter.select | test_exists_uses_cardinality_not_projection, test_exists_still_evaluates_where_and_having | EXISTS(SELECT 1/0 FROM t) comprueba existencia sin dividir |
| Guardado seguro del editor | file_io + gui | test_audit_fixes: escritura parcial, reemplazo fallido y guardado correcto | Fallo de escritura conserva archivo y cambios del editor |
| 8 CLI/GUI/core compartido | api + cli + gui | test_boundaries: flujo CLI, GUI offscreen y cancelación de documento | `python -m sql_interpreter gui` |
| Analizar sin escrituras/ejecución explícita | APIs separadas | test_analysis_does_not_open_files_for_write, test_analyze_simulates_catalog_without_files, test_gui_explicit_execution_and_panels | Analizar CREATE seguido de SELECT no crea base |

Ejemplos ejecutables completos: `examples/demo.sql`, `examples/queries.sql`, `examples/invalid.sql`. El último contiene un error deliberado y debe fallar sin publicar la sentencia inválida.

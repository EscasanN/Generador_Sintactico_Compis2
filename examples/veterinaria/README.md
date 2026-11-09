# Veterinaria: demostración completa

Elegir una base NUEVA, por ejemplo `tmp/veterinaria-completa-01`. Ejecutar cada archivo por separado en el orden indicado. La GUI ejecuta TODO el editor, no únicamente la selección. Los CREATE e INSERT se ejecutan una sola vez. Para repetir desde cero elegir otra ruta.

| Archivo | Qué demostrar y resultado esperado |
|---|---|
| 01_crear_datos.sql | Antes de ejecutar: Analizar, Tokens, Árbol y AST sin crear la base. Después: CREATE e INSERT, cinco tipos, PRIMARY KEY, UNIQUE, NOT NULL y llaves foráneas. Son seis sentencias modificadoras: seis generaciones. |
| 02_consultas.sql | Doce consultas; seleccionar cada resultado en el desplegable. Véase la tabla de abajo. Se puede repetir antes de 05, que cambia las edades. |
| 03_busqueda_sin_indice.sql | Milo; 4 row_reads, 1 table_scan. Consultar tooltip de Resultados. |
| 04_crear_indice.sql | Milo; 1 row_read, 0 table_scans, 1 index_lookup. |
| 05_cambios.sql | UPDATE mueve a Milo a edad 3 y vacunada True. Edad 2 queda vacía; insertar Toby devuelve Milo/Toby; borrarlo devuelve solo Milo. El índice se mantiene actualizado. |
| 06_reabrir.sql | Cerrar y reabrir GUI con la misma carpeta. Milo/3/True; cuatro mascotas. El índice persiste. |
| errores/*.sql | Ejecutar UNO por vez. Deben fallar sin cambiar los datos; doble clic al diagnóstico para ir a línea/columna. Algunos dependen de que exista idx_edad, por eso probarlos antes de 07. |
| 07_eliminar_indice_y_tabla_temporal.sql | DROP INDEX, misma respuesta con scan; CREATE/INSERT/SELECT/DROP de tabla temporal. No borra mascotas. |
| 08_borrado_ordenado_OPCIONAL.sql | DESTRUCTIVO. Solo al finalizar y si no necesitas los datos: elimina primero consultas, luego mascotas y luego duenos. |

## Resultados de 02_consultas.sql

| N.º | Resultado esperado |
|---|---|
| 1 | Coco/8; Milo/2; Nina/1 |
| 2 | 1/Luna/Marta/150.0; 2/Luna/Marta/200.0; 3/Milo/Diego/120.0 |
| 3 | Luna / 2 consultas / suma 350.0 / promedio 175.0 / mínimo 150.0 / máximo 200.0 |
| 4 | Luna, Milo |
| 5 | Coco, Nina |
| 6 | Luna, Milo |
| 7 | Coco, Nina |
| 8 | Coco/8 |
| 9 | 2/200.0 |
| 10 | 2/2026-10-05/200.0 |
| 11 | Coco |
| 12 | 4 filas / 3 pesos no nulos |

## La corrección que pidió el profesor

La relación persistente es `duenos <- mascotas <- consultas`. `DROP TABLE mascotas` se rechaza porque consultas la referencia, aunque consultas esté vacía. `DROP TABLE duenos` se rechaza porque mascotas la referencia. Las relaciones están declaradas con REFERENCES: no se deducen por el nombre de una columna o por un JOIN.

Ejecutar `errores/01_drop_mascotas.sql` y mostrar que el error menciona consultas. Reabrir la misma base y repetir: la protección permanece. Borrar filas de consultas no elimina la dependencia de su esquema; para eliminar mascotas primero debe eliminarse la tabla consultas.

En bases antiguas sin referencias se deben añadir con ALTER, como explica `../foreign_keys/README.md`. No se modifican automáticamente tus bases existentes.

## Frases para la exposición

* Tokens: “Reconocemos palabras reservadas, identificadores, valores y operadores con su ubicación”.
* Árbol/AST: “El árbol representa reglas de la gramática; el AST organiza operaciones SQL”.
* Semántica: “El catálogo permite resolver nombres, tipos, alias y restricciones antes de aplicar cambios”.
* JOIN: “Combinamos filas cuando sus identificadores coinciden; una mascota puede aparecer varias veces si tiene varias consultas”.
* WHERE/HAVING: “WHERE filtra filas; HAVING filtra grupos”.
* Escalar: “Debe devolver una columna y como máximo una fila; cero filas da NULL”.
* Índice: “Obtenemos RID y abrimos directamente sus archivos; el resultado no cambia, disminuyen las lecturas”.
* Archivos: “Se prepara una generación y se publica el manifiesto al terminar. Un error de validación no publica cambios parciales”.
* Llaves foráneas: “No permitimos borrar una tabla referenciada ni dejar registros hijos sin padre; no hay CASCADE”.

Las restricciones son por sentencia, no una transacción de todo el script. El intérprete requiere un escritor a la vez. No se afirma compatibilidad completa con SQL ni índices B-tree.

# Proteger tablas referenciadas

Corrección solicitada por el profesor: no permitir `DROP TABLE estudiantes` mientras otra tabla declare una llave foránea hacia estudiantes, aunque la tabla hija esté vacía.

## Para tu base que ya existe

1. Cierra y vuelve a abrir la GUI con la versión actualizada. Selecciona tu carpeta de base habitual.
2. Abre y ejecuta **04_migrar_base_existente.sql** una sola vez. Registra la relación en el catálogo sin modificar los archivos de fila. Si hay valores de estudiante_id sin padre, se muestra un error y no se publica el cambio; hay que revisar esos datos antes de añadir la relación.
3. Si también tienes cursos, ejecuta **04b_relacion_cursos.sql** para registrar esa segunda relación.
4. Abre **02_error_drop_estudiantes.sql**. Analizar y Ejecutar deben rechazarlo, indicando que inscripciones referencia estudiantes. Comprueba que SELECT sigue recuperando ambas tablas.

No se deducen llaves foráneas por nombres como estudiante_id ni por haber usado un JOIN. En bases antiguas la relación no existe hasta declararla con ALTER. No hace falta borrar la base ni editar JSON a mano.

## Para una demostración nueva

Usa una carpeta vacía, por ejemplo `tmp/demo-foreign-keys-01`.

* **01_demo_nueva_base.sql**: crea tres tablas, declara referencias de columna y de tabla e inserta datos válidos. El JOIN devuelve Ana / Compiladores.
* **02_error_drop_estudiantes.sql**: muestra el error que pidió el profesor.
* **03_error_insert_huerfana.sql**: impide una inscripción del estudiante 99.
* Cierra/reabre la GUI con la misma carpeta y repite el DROP: la protección persiste.
* **05_borrado_ordenado.sql**: demostración destructiva opcional; elimina primero la hija y después los padres. No ejecutar en tu base de trabajo.

Los archivos con error deben ejecutarse por separado: el primer error detiene el script.

## Reglas implementadas

* Llaves foráneas simples hacia una columna PRIMARY KEY o UNIQUE con el mismo tipo y longitud VARCHAR.
* `columna INT REFERENCES padre(id)`, `FOREIGN KEY (columna) REFERENCES padre(id)` y `ALTER TABLE hija ADD FOREIGN KEY (...) REFERENCES ...`.
* Valores NULL permitidos si la columna no es NOT NULL.
* INSERT/UPDATE de la hija requieren un padre existente; DELETE/UPDATE de la clave del padre no pueden dejar referencias huérfanas.
* DROP del padre se bloquea por la dependencia de esquema, aun sin filas en la hija. Borrar las filas hijas no elimina la restricción.
* Validación antes de publicar, persistencia en catálogo y errores con ubicación compartidos por GUI y CLI.
* Sin CASCADE, claves compuestas, nombres de restricciones ni DROP CONSTRAINT. Una tabla que solo se referencia a sí misma puede eliminarse.

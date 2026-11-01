-- Ejecutar después de demo.sql sobre el mismo almacenamiento.
SELECT * FROM estudiantes ORDER BY id;
SELECT nombre FROM estudiantes WHERE id NOT IN (SELECT estudiante_id FROM inscripciones);
SELECT nombre FROM estudiantes e WHERE EXISTS (SELECT * FROM inscripciones i WHERE i.estudiante_id=e.id);
SELECT COUNT(*),SUM(nota),AVG(nota),MIN(nota),MAX(nota) FROM inscripciones;

SELECT nombre,edad FROM estudiantes WHERE edad>=18 AND (activo=TRUE OR promedio IS NULL) ORDER BY edad DESC;
SELECT e.nombre,c.nombre,i.nota
FROM estudiantes e INNER JOIN inscripciones i ON e.id=i.estudiante_id
INNER JOIN cursos c ON c.id=i.curso_id
ORDER BY e.nombre,c.nombre;
SELECT curso_id,COUNT(*),SUM(nota),AVG(nota),MIN(nota),MAX(nota)
FROM inscripciones GROUP BY curso_id HAVING COUNT(*)>1 ORDER BY curso_id;
SELECT nombre FROM estudiantes WHERE id IN (SELECT estudiante_id FROM inscripciones WHERE curso_id=3) ORDER BY nombre;
SELECT nombre FROM estudiantes WHERE id NOT IN (SELECT estudiante_id FROM inscripciones) ORDER BY nombre;
SELECT nombre FROM estudiantes e WHERE EXISTS(SELECT * FROM inscripciones i WHERE i.estudiante_id=e.id) ORDER BY nombre;
SELECT nombre FROM estudiantes e WHERE NOT EXISTS(SELECT * FROM inscripciones i WHERE i.estudiante_id=e.id) ORDER BY nombre;
SELECT nombre FROM estudiantes WHERE edad=(SELECT MAX(edad) FROM estudiantes);

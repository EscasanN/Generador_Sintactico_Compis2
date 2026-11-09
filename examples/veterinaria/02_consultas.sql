-- 1: WHERE, AND, OR y ORDER BY. Coco/8, Milo/2, Nina/1.
SELECT nombre,edad FROM mascotas
WHERE (especie='Gato' AND vacunada=FALSE) OR peso IS NULL ORDER BY edad DESC;

-- 2: Dos INNER JOIN y alias.
SELECT c.id,m.nombre,d.nombre,c.costo FROM consultas c
INNER JOIN mascotas m ON c.mascota_id=m.id
INNER JOIN duenos d ON m.dueno_id=d.id ORDER BY c.id;

-- 3: Cinco agregaciones, GROUP BY y HAVING.
SELECT m.nombre,COUNT(*),SUM(c.costo),AVG(c.costo),MIN(c.costo),MAX(c.costo)
FROM mascotas m INNER JOIN consultas c ON m.id=c.mascota_id
GROUP BY m.nombre HAVING COUNT(*)>1 ORDER BY m.nombre;

-- 4: IN. Luna, Milo.
SELECT nombre FROM mascotas WHERE id IN (SELECT mascota_id FROM consultas) ORDER BY nombre;
-- 5: NOT IN. Coco, Nina.
SELECT nombre FROM mascotas WHERE id NOT IN (SELECT mascota_id FROM consultas) ORDER BY nombre;
-- 6: EXISTS correlacionado. Luna, Milo.
SELECT nombre FROM mascotas m WHERE EXISTS(SELECT * FROM consultas c WHERE c.mascota_id=m.id) ORDER BY nombre;
-- 7: NOT EXISTS correlacionado. Coco, Nina.
SELECT nombre FROM mascotas m WHERE NOT EXISTS(SELECT * FROM consultas c WHERE c.mascota_id=m.id) ORDER BY nombre;

-- 8: Escalar con MAX. Coco/8.
SELECT nombre,edad FROM mascotas WHERE edad=(SELECT MAX(edad) FROM mascotas);
-- 9: Escalar con AVG en comparacion. Consulta 2/200.0.
SELECT id,costo FROM consultas WHERE costo>(SELECT AVG(costo) FROM consultas);
-- 10: Fechas. Consulta 2/2026-10-05/200.0.
SELECT id,fecha,costo FROM consultas WHERE fecha>=DATE '2026-10-03' ORDER BY fecha;
-- 11: NULL. Coco.
SELECT nombre FROM mascotas WHERE peso IS NULL;
-- 12: COUNT(*) frente a COUNT(columna): 4/3.
SELECT COUNT(*),COUNT(peso) FROM mascotas;

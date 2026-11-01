CREATE TABLE estudiantes (
    id INT PRIMARY KEY,
    nombre VARCHAR(40) NOT NULL,
    edad INT,
    promedio FLOAT,
    activo BOOLEAN,
    nacimiento DATE
);
CREATE TABLE inscripciones (id INT PRIMARY KEY, estudiante_id INT, curso_id INT, nota FLOAT);
INSERT INTO estudiantes VALUES
    (1, 'Ana', 20, 88.5, TRUE, DATE '2006-02-28'),
    (2, 'Luis', 17, 75, TRUE, DATE '2009-05-12'),
    (3, 'María', 22, NULL, FALSE, DATE '2004-08-03');
INSERT INTO inscripciones VALUES (1,1,3,90),(2,1,4,85),(3,2,3,75);
CREATE INDEX idx_edad ON estudiantes(edad);
SELECT nombre, edad FROM estudiantes WHERE edad >= 18 ORDER BY edad DESC;
SELECT e.nombre, COUNT(*) AS cursos, AVG(i.nota) AS promedio
FROM estudiantes e INNER JOIN inscripciones i ON e.id = i.estudiante_id
GROUP BY e.nombre HAVING COUNT(*) >= 1 ORDER BY promedio DESC;
SELECT nombre FROM estudiantes WHERE id IN (SELECT estudiante_id FROM inscripciones WHERE curso_id = 3);
SELECT nombre FROM estudiantes e WHERE NOT EXISTS (SELECT * FROM inscripciones i WHERE i.estudiante_id = e.id);
SELECT nombre FROM estudiantes WHERE edad = (SELECT MAX(edad) FROM estudiantes);
UPDATE estudiantes SET edad = edad + 1 WHERE id = 1;
DELETE FROM inscripciones WHERE nota < 80;
SELECT nombre, edad FROM estudiantes WHERE edad >= 18 ORDER BY edad;

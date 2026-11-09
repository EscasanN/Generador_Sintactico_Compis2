-- Ejecutar una sola vez en una carpeta de base NUEVA.
CREATE TABLE estudiantes (id INT PRIMARY KEY, nombre VARCHAR(30) NOT NULL);
CREATE TABLE cursos (id INT PRIMARY KEY, nombre VARCHAR(30));
CREATE TABLE inscripciones (
    id INT PRIMARY KEY,
    estudiante_id INT REFERENCES estudiantes(id),
    curso_id INT,
    FOREIGN KEY (curso_id) REFERENCES cursos(id)
);
INSERT INTO estudiantes VALUES (1,'Ana'),(2,'Luis');
INSERT INTO cursos VALUES (3,'Compiladores');
INSERT INTO inscripciones VALUES (1,1,3);
SELECT e.nombre,c.nombre FROM inscripciones i
INNER JOIN estudiantes e ON i.estudiante_id=e.id
INNER JOIN cursos c ON i.curso_id=c.id;

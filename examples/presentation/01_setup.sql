CREATE TABLE estudiantes (
    id INT PRIMARY KEY,
    nombre VARCHAR(20) NOT NULL,
    edad INT,
    promedio FLOAT,
    activo BOOLEAN,
    nacimiento DATE
);
CREATE TABLE cursos (id INT PRIMARY KEY, nombre VARCHAR(20));
CREATE TABLE inscripciones (
    id INT PRIMARY KEY,
    estudiante_id INT REFERENCES estudiantes(id),
    curso_id INT REFERENCES cursos(id),
    nota FLOAT
);
INSERT INTO estudiantes VALUES
    (1,'Ana',20,90,TRUE,DATE '2004-02-29'),
    (2,'Luis',17,75,TRUE,DATE '2009-05-12'),
    (3,'María',22,NULL,FALSE,DATE '2004-08-03'),
    (4,'Pedro',19,60,TRUE,DATE '2007-01-01');
INSERT INTO cursos VALUES (3,'Compiladores'),(4,'Bases de datos');
INSERT INTO inscripciones VALUES (1,1,3,90),(2,1,4,80),(3,2,3,70),(4,3,3,95);

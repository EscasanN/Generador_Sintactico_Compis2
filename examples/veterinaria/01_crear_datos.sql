-- Una sola vez en una carpeta de base NUEVA.
CREATE TABLE duenos (id INT PRIMARY KEY,nombre VARCHAR(30) NOT NULL);
CREATE TABLE mascotas (
    id INT PRIMARY KEY,
    nombre VARCHAR(30) NOT NULL,
    chip VARCHAR(10) UNIQUE,
    dueno_id INT REFERENCES duenos(id),
    especie VARCHAR(10),
    edad INT,
    peso FLOAT,
    vacunada BOOLEAN,
    registro DATE
);
CREATE TABLE consultas (id INT PRIMARY KEY,mascota_id INT REFERENCES mascotas(id),fecha DATE,costo FLOAT);
INSERT INTO duenos VALUES (1,'Marta'),(2,'Diego'),(3,'Luz');
INSERT INTO mascotas VALUES
    (1,'Luna','CHIP01',1,'Perro',5,12.5,TRUE,DATE '2026-09-01'),
    (2,'Milo','CHIP02',2,'Gato',2,4.2,FALSE,DATE '2026-09-02'),
    (3,'Coco','CHIP03',1,'Perro',8,NULL,TRUE,DATE '2026-09-03'),
    (4,'Nina','CHIP04',3,'Gato',1,3.1,FALSE,DATE '2026-09-04');
INSERT INTO consultas VALUES
    (1,1,DATE '2026-10-01',150),
    (2,1,DATE '2026-10-05',200),
    (3,2,DATE '2026-10-02',120);

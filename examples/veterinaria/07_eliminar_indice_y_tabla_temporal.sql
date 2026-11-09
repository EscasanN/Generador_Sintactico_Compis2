DROP INDEX idx_edad;
SELECT nombre FROM mascotas WHERE edad=3;
CREATE TABLE recordatorios(id INT PRIMARY KEY,descripcion VARCHAR(40));
INSERT INTO recordatorios VALUES (1,'Llamar al dueno de Milo');
SELECT * FROM recordatorios;
DROP TABLE recordatorios;

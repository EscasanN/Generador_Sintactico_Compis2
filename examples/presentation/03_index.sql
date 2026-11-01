CREATE INDEX idx_edad ON estudiantes(edad);
SELECT nombre FROM estudiantes WHERE 20=edad;
UPDATE estudiantes SET edad=21 WHERE id=1;
SELECT nombre,edad FROM estudiantes WHERE edad=21;
SELECT nombre FROM estudiantes WHERE edad=20;
INSERT INTO estudiantes VALUES (5,'Eva',21,85,TRUE,DATE '2005-01-01');
SELECT nombre FROM estudiantes WHERE edad=21 ORDER BY nombre;
DELETE FROM estudiantes WHERE id=5;
SELECT nombre FROM estudiantes WHERE edad=21;

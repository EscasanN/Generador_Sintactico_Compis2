UPDATE mascotas SET edad=3,vacunada=TRUE WHERE id=2;
SELECT nombre FROM mascotas WHERE edad=2;
SELECT nombre,edad,vacunada FROM mascotas WHERE edad=3;
INSERT INTO mascotas VALUES (5,'Toby','CHIP05',3,'Perro',3,8.5,FALSE,DATE '2026-11-01');
SELECT nombre FROM mascotas WHERE edad=3 ORDER BY nombre;
DELETE FROM mascotas WHERE id=5;
SELECT nombre FROM mascotas WHERE edad=3;

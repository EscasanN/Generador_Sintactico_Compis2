-- Sobre la base demo: fecha imposible, no modifica ninguna fila.
UPDATE estudiantes SET nacimiento=DATE '2023-02-29' WHERE id=1;

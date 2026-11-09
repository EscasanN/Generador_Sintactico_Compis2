-- Para una base anterior que YA tiene estudiantes e inscripciones.
-- Registrar la relacion sin borrar ni recrear tablas; ejecutar una sola vez.
-- Si hay inscripciones huerfanas, se rechaza sin alterar la base.
ALTER TABLE inscripciones ADD FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id);

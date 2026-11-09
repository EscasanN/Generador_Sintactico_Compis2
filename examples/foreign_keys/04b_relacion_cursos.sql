-- Opcional: solo si la base anterior tambien tiene la tabla cursos.
ALTER TABLE inscripciones ADD FOREIGN KEY (curso_id) REFERENCES cursos(id);

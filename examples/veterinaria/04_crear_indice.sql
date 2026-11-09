CREATE INDEX idx_edad ON mascotas(edad);
-- Mismo resultado, una lectura, cero scans y un lookup.
SELECT nombre FROM mascotas WHERE 2=edad;

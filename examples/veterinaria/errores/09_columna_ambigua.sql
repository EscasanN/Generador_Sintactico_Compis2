-- Error deliberado. Ejecutar individualmente antes del archivo 07.
SELECT id FROM mascotas m INNER JOIN consultas c ON m.id=c.mascota_id;

-- Error deliberado. Ejecutar individualmente antes del archivo 07.
SELECT nombre FROM mascotas WHERE edad=(SELECT edad FROM mascotas);

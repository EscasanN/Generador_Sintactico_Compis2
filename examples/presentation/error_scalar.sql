SELECT nombre FROM estudiantes WHERE edad=(SELECT edad FROM estudiantes);

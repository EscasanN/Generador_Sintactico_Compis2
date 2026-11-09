# Guía para presentar el intérprete SQL

## Antes de entrar a la presentación

Ensayen con los archivos de `examples/presentation/`. Reserven unos 15–20 minutos y ajusten al tiempo del profesor. Un integrante puede explicar frontend y AST, otro semántica e interpretación y otro almacenamiento, índices y pruebas; todos deben entender el recorrido completo.

En el equipo de presentación, desde la raíz del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m sql_interpreter gui --database tmp/base-presentacion-01
```

El directorio elegido para la base debe ser nuevo. Para repetir el ensayo, cambien `01` por `02` y así sucesivamente. No borren generaciones dentro de una base existente: puede haber archivos todavía referenciados. No usen para exponer la base de QA, porque el ensayo automatizado termina con operaciones de limpieza.

La instalación normal necesita acceso a las dependencias de PyPI. En este entorno esa conexión estaba bloqueada y el ensayo se realizó con dependencias locales copiadas a un venv aislado. Instalen y prueben el ambiente del equipo real antes del día de exposición; no dependan de Internet en el aula. El parser generado está incluido y no necesita Java ni descargas durante la demostración.

Tengan abiertas la GUI, la carpeta de la base, este documento y el informe `docs/presentation-results.md`. Los archivos `.sql` son el respaldo por si necesitan volver a una consulta; la CLI sirve como alternativa si falla la pantalla gráfica.

## Guion de la demostración

| Tiempo orientativo | Acción | Qué demuestra |
|---|---|---|
| 0–2 min | Explicar el recorrido y los componentes | Cumplimiento del objetivo del documento |
| 2–5 min | Analizar `01_setup.sql`, recorrer tokens/árbol/AST y luego ejecutar | Análisis separado de ejecución y esquema tipado |
| 5–8 min | Ejecutar `02_queries.sql` | Filtros, JOIN, agregaciones, GROUP BY y HAVING |
| 8–11 min | Explicar sus subconsultas y provocar dos errores | IN/EXISTS/escalares, validación y ubicación |
| 11–15 min | Probar índice, DML y reabrir | Índices reales, consistencia y persistencia |
| 15–18 min | Mostrar pruebas, límites y responder preguntas | Evidencia y dominio del diseño |

### 1. Apertura: qué construyeron

Pueden comenzar así:

> “Construimos un intérprete para el subconjunto SQL del enunciado. El texto pasa por un lexer y parser generados desde nuestra gramática ANTLR; de ahí construimos un AST propio, validamos nombres y tipos y evaluamos las operaciones sobre nuestro almacenamiento en archivos. La interfaz y la CLI consumen el mismo núcleo.”

Muestren este recorrido:

```text
SQL → tokens → árbol sintáctico → AST SQL → semántica
    → prevalidación de datos → interpretación → archivos → resultados
```

Aclaren que ANTLR resuelve reconocimiento léxico/sintáctico. No ejecuta consultas, valida esquemas ni proporciona una base de datos. Esas partes son propias.

### 2. Analizar no crea la base

Abrir `examples/presentation/01_setup.sql`. Antes de ejecutar, pulsar **Analizar** y mostrar las pestañas Tokens, Árbol sintáctico y AST. Mostrar que el directorio de almacenamiento todavía no se creó.

> “Analizar reconoce y valida sin aplicar CREATE ni INSERT. Puede simular los cambios de catálogo en memoria para reconocer referencias posteriores del mismo script, pero no persiste los cambios.”

Después pulsar **Ejecutar**. Se crean tres tablas y se insertan estudiantes, cursos e inscripciones. Mostrar `manifest.json` y el catálogo vigente; no abrir archivos al azar de generaciones antiguas como si fueran el estado actual.

Los estudiantes son:

| id | nombre | edad | promedio | activo | nacimiento |
|---:|---|---:|---:|---|---|
| 1 | Ana | 20 | 90.0 | TRUE | 2004-02-29 |
| 2 | Luis | 17 | 75.0 | TRUE | 2009-05-12 |
| 3 | María | 22 | NULL | FALSE | 2004-08-03 |
| 4 | Pedro | 19 | 60.0 | TRUE | 2007-01-01 |

Explicar la conversión INT → FLOAT con el promedio 90 almacenado como 90.0; BOOLEAN se conserva como booleano, no como entero. El catálogo conserva que nacimiento es DATE, aunque su representación JSON sea una cadena ISO.

### 3. Diferencia entre árbol sintáctico y AST

Usar como ejemplo:

```sql
SELECT nombre FROM estudiantes WHERE edad >= 18;
```

El árbol sintáctico refleja reglas y terminales de la gramática, incluidos SELECT, FROM, operadores y reglas intermedias. El AST organiza la intención SQL: una consulta Select con proyección de nombre, referencia a estudiantes y condición binaria edad >= 18. No conserva cada regla intermedia ni necesita los signos de puntuación como nodos de ejecución.

> “La distinción nos permite cambiar detalles de la gramática sin acoplar el almacenamiento o la interpretación a clases generadas por ANTLR.”

### 4. Consultas, JOIN y agregación

Ejecutar `02_queries.sql` y seleccionar los resultados de cada sentencia en el desplegable de la pestaña Resultados.

La primera consulta combina AND, OR y ORDER BY. Devuelve María/22, Ana/20 y Pedro/19 en ese orden. Señalar que `promedio IS NULL` acepta a María aunque activo sea FALSE.

El JOIN une estudiantes, inscripciones y cursos mediante IDs. Debe mostrar:

| Estudiante | Curso | Nota |
|---|---|---:|
| Ana | Bases de datos | 80.0 |
| Ana | Compiladores | 90.0 |
| Luis | Compiladores | 70.0 |
| María | Compiladores | 95.0 |

En la consulta agrupada, para curso 3 se esperan COUNT=3, SUM=255.0, AVG=85.0, MIN=70.0 y MAX=95.0. El curso 4 tiene un registro y HAVING COUNT(*)>1 lo excluye.

> “WHERE filtra filas antes de agrupar. GROUP BY reúne las filas por clave. HAVING filtra grupos, y ORDER BY ordena el resultado. No podemos proyectar una columna arbitraria de un grupo si no está agrupada o agregada.”

### 5. Subconsultas

En el mismo archivo:

* IN del curso 3 devuelve Ana, Luis y María.
* NOT IN de las inscripciones devuelve Pedro, que no tiene inscripciones.
* EXISTS correlacionado devuelve Ana, Luis y María; NOT EXISTS devuelve Pedro.
* La comparación escalar contra MAX(edad) devuelve María.

> “Una subconsulta correlacionada depende de la fila exterior: `i.estudiante_id=e.id`. Resolvemos los nombres en el ámbito más cercano y después en los exteriores. Una no correlacionada es independiente y podemos reutilizar su resultado dentro de la misma sentencia.”

La cardinalidad escalar es una columna y como máximo una fila. Cero filas produce NULL; más de una fila se rechaza. Una agregación como MAX sin GROUP BY produce una fila, incluso si su valor resulta NULL.

Abrir `error_scalar.sql` y pulsar Analizar sobre la base existente: debe aparecer el diagnóstico de más de una fila. No se modifica el almacenamiento. Explicar que analizar sin datos solo puede validar estructura y tipos; en scripts, después de la primera sentencia modificadora no se anticipan los datos futuros. Ejecutar prevalida cada sentencia sobre el estado vigente antes de aplicar cambios.

### 6. Errores localizados y ausencia de modificaciones parciales

Abrir `error_date.sql`: el 29 de febrero de 2023 no existe. Mostrar el mensaje y la ubicación. Volver a consultar a Ana y comprobar que su fecha sigue siendo 2004-02-29.

Si hay tiempo, pegar una consulta inválida cada vez:

```sql
SELECT @ FROM estudiantes;
SELECT FROM estudiantes;
SELECT desconocida FROM estudiantes;
UPDATE estudiantes SET edad='veinte' WHERE id=1;
```

La primera es léxica; la segunda sintáctica; las restantes son semánticas. Usar doble clic sobre la fila del error para navegar a su ubicación. No ejecutar todas juntas: un error de reconocimiento rechaza el script completo y ocultaría el resto de la demostración.

> “La atomicidad que ofrecemos es por sentencia. Si un INSERT de varias filas viola una restricción, no publica ninguna de esas filas. En un script, las sentencias anteriores que terminaron correctamente permanecen.”

### 7. Índice real y mantenimiento

Antes de ejecutar `03_index.sql`, pegar únicamente:

```sql
SELECT nombre FROM estudiantes WHERE 20=edad;
```

Sin índice devuelve Ana y lee cuatro filas. Después abrir y ejecutar `03_index.sql`. Su primera consulta realiza la misma búsqueda tras crear idx_edad: devuelve Ana con una lectura de fila y cero recorridos completos de tabla.

Las estadísticas están en la salida CLI JSON; en GUI se pueden consultar en el tooltip de la tabla de resultados. Para la evidencia más clara, usar los valores antes/después del informe y los JSON del ensayo automatizado. No decir que un mensaje de “índice usado” es la prueba: las pruebas también prohíben llamar a scan en consultas compatibles.

El resto del archivo:

1. Cambia la edad de Ana a 21; la búsqueda por 21 la encuentra y por 20 ya no.
2. Inserta Eva con 21; la búsqueda devuelve Ana y Eva.
3. Borra a Eva; la búsqueda vuelve a devolver solo Ana.

> “El índice guarda claves tipadas y listas de identificadores de fila. Con esos RID recuperamos los archivos de fila directamente. No recorremos los registros para encontrar dónde están las coincidencias.”

Aclaren que el WHERE por id de estas modificaciones no tiene un índice sobre id en este ejemplo; el objetivo aquí es demostrar que el índice de edad se mantiene correcto. La suite contiene además un UPDATE indexado que lee y escribe una sola fila sin scan, cuando no necesita recorrer la tabla para verificar UNIQUE.

### 8. Persistencia y cierre

Cerrar la GUI y abrirla de nuevo con el mismo directorio de base. Ejecutar `04_reopen.sql`: devuelve Ana/21 y los grupos curso 3/3 inscripciones y curso 4/1 inscripción.

Por último, `05_cleanup.sql` demuestra DROP INDEX, CREATE TABLE, INSERT y DROP TABLE de una tabla temporal. No elimina las tablas principales.

## Explicaciones técnicas que deben dominar

**Catálogo.** Es el registro de tablas, columnas, tipos, restricciones e índices. No es una tabla de símbolos de variables Compiscript. Permite detectar tablas inexistentes, columnas ambiguas y tipos incompatibles antes de modificar datos.

**Interpretación.** No se genera TAC ni código máquina. El intérprete recorre nodos SQL y opera con filas y valores. INNER JOIN utiliza evaluación de combinaciones de filas; la versión actual no es un optimizador de uniones industrial.

**Almacenamiento.** El manifiesto señala una generación. `rows.json` indica en qué generación está cada RID; `indexes.json` hace lo mismo con los índices. Las filas y los índices son archivos JSON UTF-8. JSON se usa solo para serializar valores; no procesa SQL.

**Publicación.** Primero se validan los cambios, se escriben archivos nuevos y luego se reemplaza el manifiesto. Los archivos anteriores son inmutables y pueden compartirse. Una modificación no copia todas las filas de todas las tablas. Se siguen reescribiendo los metadatos y los índices afectados completos.

**Restricciones.** PRIMARY KEY implica UNIQUE y NOT NULL; las claves son simples. UNIQUE permite varios NULL. Validar unicidad puede recorrer la tabla afectada para comparar su estado final; no se afirma costo constante ni ausencia total de recorridos para todas las modificaciones.

**Llaves foráneas y DROP (corrección del profesor).** La versión actual registra REFERENCES/FOREIGN KEY en el catálogo. No deja eliminar estudiantes mientras exista inscripciones con una referencia hacia ella, aunque la hija esté vacía; hay que eliminar primero la tabla hija. También evita registros hijos sin padre y cambios/borrados de claves que rompan la relación. Las bases creadas antes requieren añadir las referencias con ALTER TABLE; abrirlas no inventa esas relaciones. Los archivos de demostración y migración están en `examples/foreign_keys/`. Para otro dominio, `examples/veterinaria/` contiene la demostración completa con dependencias `duenos <- mascotas <- consultas`.

**NULL.** No es cero ni cadena vacía. Las comparaciones ordinarias con NULL producen desconocido. WHERE acepta solo TRUE. `COUNT(*)` cuenta filas, `COUNT(columna)` omite NULL. `NOT IN` con NULL en el conjunto puede producir desconocido; EXISTS depende de si hay filas y no evalúa la proyección para obtener sus valores.

**GUI y worker.** El núcleo no importa Qt. La GUI envía una copia del texto a un worker para no bloquear la interfaz, y controla la revisión del documento para evitar presentar resultados de texto anterior como si correspondieran al nuevo.

**Reutilización.** Se reutilizaron/adaptaron infraestructura neutral de ANTLR, modelo de árbol, diagnósticos y patrones de documentos/worker/pruebas. La procedencia está en `docs/provenance.md`. No se copió todo Compiscript ni se depende de su ruta local.

## Preguntas probables del profesor

| Pregunta | Respuesta defendible |
|---|---|
| ¿Por qué ANTLR? | Genera lexer y parser desde la gramática propia y permite concentrar la lógica del proyecto en AST, semántica, ejecución y almacenamiento. |
| ¿Por qué JSON y no CSV? | El enunciado permite definir el formato. JSON conserva booleanos, números y NULL y permite serializar catálogo e índices; sigue siendo texto y no es un DBMS. |
| ¿Es un índice B-tree? | No. Es un mapa persistido de claves tipadas a RID. Igualdad consulta la clave; rangos examinan claves del índice. No prometemos complejidad logarítmica. |
| ¿Cómo sabemos que no hacen un scan oculto? | Tenemos contadores de lecturas y pruebas que fallan si se llama a scan; comprobamos los resultados y los archivos de fila recuperados. |
| ¿Qué pasa si falla una escritura? | Antes de publicar el manifiesto sigue vigente la generación anterior. Puede quedar una generación huérfana, pero no se usa. No prometemos recuperación total ante corte eléctrico. |
| ¿Se pueden borrar las generaciones antiguas? | No manualmente: la generación vigente puede referenciarlas. Haría falta una recolección de archivos alcanzables que no está implementada. |
| ¿Puede haber varios escritores? | El alcance documentado admite un escritor por directorio; no presentamos concurrencia entre procesos como capacidad implementada. |
| ¿Analizar ejecuta el SQL? | No aplica cambios. Sí puede evaluar consultas de lectura para comprobar cardinalidad sobre datos existentes. Sin almacenamiento solo valida estructura y tipos. |
| ¿Todas las condiciones usan índice? | Se reconocen patrones compatibles: comparaciones con constantes/escalares independientes, IN/NOT IN independientes y combinaciones compatibles. Expresiones arbitrarias y correlación general conservan evaluación ordinaria. |
| ¿Por qué rechazaron subconsultas en ON? | El dialecto elegido limita subconsultas a WHERE, que es el alcance pedido por el documento. |
| ¿Qué garantiza el número de pruebas? | Que esos escenarios fueron verificados. No garantiza ausencia absoluta de errores ni una nota específica. |

## Qué evitar afirmar

No afirmar compatibilidad completa con SQL, índices B-tree, transacciones de scripts completos, concurrencia, cero scans en toda operación o recuperación garantizada ante corte eléctrico. Tampoco afirmar que una instalación desde PyPI se comprobó en este equipo: la conexión fue bloqueada. Expliquen con precisión la diferencia entre la prueba aislada offline realizada y la instalación normal que ensayarán en el equipo de presentación.

Cerrar con una frase concreta:

> “Mostramos el recorrido completo desde SQL hasta archivos propios, los resultados esperados, los errores con ubicación, la persistencia al reabrir y evidencia de acceso por índices. El informe conserva los resultados y los comandos para repetir la demostración.”

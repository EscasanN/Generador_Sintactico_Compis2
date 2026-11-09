# Auditoría de compatibilidad con SQL habitual — 5 de noviembre de 2026

Se inspeccionaron gramática, AST, semántica, planificación, interpretación y almacenamiento. Se ejecutaron **40 consultas adicionales** sobre una base nueva bajo `tmp/audit-common-sql-c9zo4a2n`. No se utilizó otro DBMS para procesar SQL ni se modificaron datos de DB/ o database/. La suite existente pasó: **178 passed in 24.22s**.

Esta revisión no cambia la implementación. El alcance original es un subconjunto de SQL; muchas ausencias no son incumplimientos del enunciado. No existe un único comportamiento universal entre todos los dialectos. Se utilizaron referencias oficiales para las formas habituales de ORDER BY, restricciones e IN con lista.

## Primero: comportamientos aceptados o combinados de manera problemática

### 1. ORDER BY con posición devuelve un orden distinto al habitual

Datos insertados en este orden: Milo, Luna, Coco.

```sql
SELECT nombre FROM mascotas ORDER BY 1;
```

Aceptado, pero devuelve Milo, Luna, Coco. La forma SQL habitual interpreta 1 como la primera columna proyectada y ordenaría Coco, Luna, Milo. `ORDER BY nombre` sí devuelve ese orden correcto.

Causa: `interpreter.py` evalúa el literal 1 como clave constante de todas las filas; `semantic.py` no resuelve ordinales contra la proyección. Es una incompatibilidad silenciosa: conviene implementar ordinales o rechazarlos explícitamente, evitando aparentar que están soportados.

### 2. ORDER BY con posición inexistente no da error

```sql
SELECT nombre FROM mascotas ORDER BY 9;
```

Aceptado sin error y devuelve el orden de lectura, aunque la proyección tiene una sola columna. Comparte la causa anterior. Debe comprobarse el rango si se admiten ordinales.

### 3. SELECT * y GROUP BY de todas las columnas no se combinan

```sql
SELECT * FROM mascotas GROUP BY id,nombre,edad,peso,vacunada;
```

Las cinco columnas son todas las de la tabla de auditoría. La consulta se rechaza con `Columna fuera de GROUP BY`. El validador rechaza el comodín antes de comprobar sus columnas expandidas. Es una combinación incompleta de dos capacidades disponibles, no un fallo de persistencia. Escribir explícitamente la lista de columnas evita el comodín.

## Funciones comunes que se rechazan porque faltan

| Capacidad | Ejemplo probado | Observación |
|---|---|---|
| IN / NOT IN con lista | `WHERE id IN (1,2)` | Solo se admite IN/NOT IN con subconsulta SELECT. |
| LIKE | `WHERE nombre LIKE 'L%'` | No hay búsqueda por patrón. |
| BETWEEN | `WHERE edad BETWEEN 2 AND 5` | Se puede expresar como dos comparaciones con AND. |
| DISTINCT | `SELECT DISTINCT vacunada FROM mascotas` | Se interpreta distinct como identificador y termina en error semántico. |
| LIMIT | `ORDER BY edad LIMIT 2` | No hay límite de resultados. La sintaxis varía por dialecto. |
| FETCH FIRST | `FETCH FIRST 2 ROWS ONLY` | Tampoco se admite esta forma de limitar filas. |
| SELECT sin FROM | `SELECT 1+2` | Toda consulta exige tabla de origen. |
| LEFT JOIN | `mascotas m LEFT JOIN consultas c ON ...` | Solo se implementa INNER JOIN. |
| JOIN abreviado | `mascotas m JOIN consultas c ON ...` | Se exige escribir INNER JOIN. |
| UNION | `SELECT id FROM mascotas UNION SELECT mascota_id FROM consultas` | Sin combinación de resultados por conjuntos. |
| COUNT DISTINCT | `SELECT COUNT(DISTINCT mascota_id) FROM consultas` | Solo agregaciones ordinarias, sin DISTINCT. |
| Funciones de texto | `SELECT LOWER(nombre) FROM mascotas` | Solo las cinco funciones agregadas están disponibles. |
| COALESCE | `SELECT COALESCE(peso,0) FROM mascotas` | No hay función para sustituir NULL. |
| CASE | `SELECT CASE WHEN vacunada=TRUE THEN 'si' ELSE 'no' END FROM mascotas` | Sin expresiones condicionales CASE. |
| Identificadores entre comillas | `SELECT "nombre" FROM mascotas` | Solo nombres sin comillas. |
| PRIMARY KEY como restricción de tabla | `CREATE TABLE prueba(id INT, PRIMARY KEY(id))` | Sí funciona `id INT PRIMARY KEY`, pero no la forma al final de la tabla. |
| Clave primaria compuesta | `PRIMARY KEY(id,otro)` | Claves de una columna solamente. |
| DEFAULT | `activo BOOLEAN DEFAULT TRUE` | Valores omitidos en INSERT pasan a NULL, sujetos a restricciones. |
| CHECK | `edad INT CHECK(edad>=0)` | No admite restricciones generales por expresión. |
| DECIMAL | `precio DECIMAL(10,2)` | Solo los cinco tipos originales. |
| CREATE IF NOT EXISTS | `CREATE TABLE IF NOT EXISTS mascotas(id INT)` | No se puede ignorar una creación repetida. |
| DROP IF EXISTS | `DROP TABLE IF EXISTS inexistente` | No se puede ignorar un DROP sobre tabla inexistente. |
| ALTER ADD COLUMN | `ALTER TABLE mascotas ADD COLUMN color VARCHAR(10)` | ALTER solo añade una llave foránea. |
| DROP CONSTRAINT | `ALTER TABLE consultas DROP CONSTRAINT fk_mascota` | No se pueden eliminar restricciones desde SQL. |
| INSERT SELECT | `INSERT INTO mascotas(id,nombre) SELECT id,nombre FROM mascotas` | INSERT requiere VALUES. |
| DEFAULT VALUES | `INSERT INTO mascotas DEFAULT VALUES` | No se admite. |
| Transacciones explícitas | `BEGIN; UPDATE ...; ROLLBACK;` | No hay BEGIN/COMMIT/ROLLBACK; la atomicidad es por sentencia. |
| Cascadas de llave foránea | `REFERENCES mascotas(id) ON DELETE CASCADE` | Política restrictiva; no hay cascadas. |
| Restricciones con nombre | `CONSTRAINT fk_mascota FOREIGN KEY(...) REFERENCES ...` | FOREIGN KEY simple funciona, sin nombre de restricción. |
| Subconsulta en proyección | `SELECT nombre,(SELECT MAX(costo) FROM consultas) FROM mascotas` | Las subconsultas están limitadas a WHERE. |
| Tabla derivada | `FROM (SELECT id FROM mascotas) x` | FROM requiere tabla almacenada. |
| NULLS LAST explícito | `ORDER BY peso NULLS LAST` | Orden predeterminado documentado, sin cláusula para cambiarlo. |
| GROUP BY con alias de proyección | `SELECT edad+1 AS siguiente,COUNT(*) FROM mascotas GROUP BY siguiente` | No resuelve ese alias; su disponibilidad depende del dialecto. |

Estas son las 34 formas rechazadas restantes. Además se probaron tres controles que sí funcionaron: ORDER BY por nombre, PRIMARY KEY en columna e IN con subconsulta.

## Prioridades recomendadas

1. **Corregir primero las incompatibilidades silenciosas de ORDER BY.** Después resolver la expansión de comodines antes de validar GROUP BY.
2. **Ampliación pequeña y útil para las preguntas del profesor:** PRIMARY KEY/UNIQUE a nivel de tabla, IN/NOT IN con lista, LIKE, BETWEEN y JOIN como abreviatura de INNER JOIN.
3. **Mejorar el uso diario de la GUI:** IF EXISTS / IF NOT EXISTS, DISTINCT y un mecanismo documentado de límite de resultados.
4. **Segunda ampliación de esquemas:** DEFAULT, CHECK, ALTER ADD COLUMN y restricciones con nombre/eliminables. Esto último permitiría administrar ciclos de dependencias sin borrados forzados ni edición de JSON.
5. **Extensiones mayores:** LEFT JOIN, INSERT SELECT, tablas derivadas, funciones generales y transacciones. No están exigidas expresamente en el documento original y requieren más decisiones y pruebas.

No es necesario implementar todo lo que ofrece un DBMS industrial para cumplir el proyecto. Las referencias declaradas y la protección de DROP solicitadas por el profesor ya están implementadas; las limitaciones señaladas de claves compuestas, nombres y cascadas son ampliaciones distintas.

## Referencias

* [ORDER BY por nombre o número de columna](https://www.postgresql.org/docs/17/queries-order.html).
* [Formas de restricciones CREATE TABLE](https://www.postgresql.org/docs/current/sql-createtable.html).
* [IN/NOT IN con listas y tratamiento de NULL](https://www.postgresql.org/docs/current/functions-comparisons.html).

Las referencias se consultaron como documentación; no se ejecutaron consultas usando PostgreSQL u otro DBMS.

# Intérprete SQL con almacenamiento en archivos

Proyecto autónomo de Construcción de Compiladores. Implementa SQL → ANTLR → árbol sintáctico → AST SQL → semántica → interpretación → archivos JSON UTF-8 → resultados. No usa DBMS, TAC ni registros de activación.

## Instalación y uso

Requiere Python 3.11 o superior. Desde esta carpeta en PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m sql_interpreter analyze examples/demo.sql --database database
.\.venv\Scripts\python.exe -m sql_interpreter execute examples/demo.sql --database database --json
.\.venv\Scripts\python.exe -m sql_interpreter gui --database database
```

El parser generado está incluido: ejecutar, analizar y probar no requiere Java ni acceso a Internet. El entorno virtual y las dependencias deben instalarse en el equipo de destino; no se utiliza el entorno de Compiscript.

El almacenamiento publica formato 2 con referencias a filas e índices inmutables. Puede abrir bases del formato 1 anterior y publicar el siguiente cambio sin modificar sus archivos originales. Se deben conservar las generaciones antiguas, porque la base vigente puede referenciarlas.

La GUI ofrece editor, archivo nuevo/abrir/guardar, selección del almacenamiento, tokens, árbol sintáctico, AST, errores navegables y selector de resultados por sentencia. **Analizar** trabaja sin escrituras al almacenamiento; **Ejecutar** es la acción explícita que aplica el script. El trabajo se realiza fuera del hilo gráfico. No cerrar mientras hay una operación pendiente.

CLI: `analyze` y `execute` requieren un archivo UTF-8 (o `-` para stdin); `--json` incluye tokens, árboles, AST, errores, resultados y contadores de acceso. Códigos: 0 correcto, 1 SQL inválido o fallo de ejecución y 2 uso/archivo/entorno inválido. Los scripts demo crean tablas: usar un directorio nuevo para repetirlos.

## SQL soportado

`CREATE/DROP TABLE`, `CREATE/DROP INDEX`, `INSERT` multirregistro, `UPDATE`, `DELETE`, `SELECT`, `WHERE`, `AND`, `OR`, `NOT`, `ORDER BY`, `INNER JOIN`, `COUNT/SUM/AVG/MIN/MAX`, `GROUP BY`, `HAVING`, subconsultas `IN/NOT IN`, `EXISTS/NOT EXISTS` y escalares en comparaciones. Incluye alias, comodines, operadores aritméticos, `IS [NOT] NULL` y comentarios. Tipos: `INT`, `FLOAT`, `VARCHAR(n)`, `BOOLEAN`, `DATE`. Restricciones simples: `NOT NULL`, `UNIQUE`, `PRIMARY KEY`.

Las decisiones y límites concretos están en [dialecto](docs/decisions.md). Las ocho entregas del enunciado son el orden de construcción del proyecto completo, no ocho productos incompletos: véase [matriz de requisitos](docs/requirements.md).

## Núcleo reutilizable

```python
from sql_interpreter.api import analyze_sql, execute_sql
from sql_interpreter.frontend import parse_sql
from sql_interpreter.storage import FileStorage

storage = FileStorage('database')  # abrir no crea archivos
syntax = parse_sql('SELECT * FROM personas;')
analysis = analyze_sql('SELECT * FROM personas;', storage.catalog)
analysis_with_data = analyze_sql('SELECT * FROM personas;', storage=storage)
execution = execute_sql('SELECT * FROM personas;', storage)
```

Cada resultado expone `accepted` y `diagnostics`; análisis/ejecución incluyen `syntax` y `ast`; ejecución agrega `results` por sentencia con columnas, filas, afectados y estadísticas. Las excepciones SQL esperadas se devuelven como diagnósticos. Las APIs no dependen de Qt. El catálogo de entrada al análisis se copia: un script puede declarar y utilizar tablas sin persistirlas.

## Parser reproducible

Solo para modificar la gramática: descargar el JAR oficial ANTLR 4.13.2 desde `https://www.antlr.org/download/antlr-4.13.2-complete.jar` y ejecutar:

```powershell
py scripts/generate_parser.py --jar tools/antlr-4.13.2-complete.jar
```

Este comando requiere Java, verifica SHA-256 y genera visitor y parser Python. El JAR no se distribuye; la ruta es explícita. La generación nunca ocurre durante el análisis. Gramática y módulos generados se distribuyen juntos.

## Archivos y pruebas

[Arquitectura y formato](docs/architecture.md), [procedencia de reutilización](docs/provenance.md), [validación](docs/validation.md). Las pruebas de almacenamiento usan directorios únicos bajo `tmp`, para funcionar también con sandbox de Windows. Las pruebas de GUI usan Qt offscreen.

Para preparar la defensa: [guía de presentación y preguntas del profesor](docs/guia-presentacion.md), [resultados del ensayo aislado](docs/presentation-results.md) y consultas en `examples/presentation/`.

Para reproducir la comprobación de instalación autónoma:

```powershell
py -m pip wheel --no-deps --no-build-isolation --wheel-dir tmp/wheels .
py scripts/verify_install.py tmp/wheels/sql_interpreter_files-1.0.0-py3-none-any.whl
```

No se inicializó Git ni se hicieron commits, push o merge. El repositorio anterior se utilizó como referencia de lectura.

# Resultado del ensayo limpio de presentación

Ejecución terminada el **31 de octubre de 2026, 22:43:43, UTC−06:00**. Resultado: **33 controles aprobados, 0 fallidos**, y **144 pruebas de la suite aprobadas en 20.27 s** contra el paquete instalado. Se verificaron resultados esperados, no solo que las consultas fueran aceptadas.

## Qué significa “limpio” en esta prueba

Se creó el venv `tmp/presentation-clean-20261031` con `include-system-site-packages = false`. Se instaló el wheel del proyecto y se ejecutaron procesos Python con `-I -B -X utf8`, fuera del árbol fuente. Se verificó que `sql_interpreter.__file__` perteneciera al `Lib/site-packages` de ese venv. La suite se lanzó con `-o pythonpath=` para no importar el paquete de `src` por la configuración de pytest.

La base y los archivos SQL del ensayo se crearon en un directorio nuevo: `tmp/presentation-run-x9mw7yrd`. Cada llamada CLI abrió un proceso nuevo, lo que también comprueba persistencia entre procesos. La GUI utilizó otra base inicialmente inexistente.

**Límite de instalación:** el intento normal de instalar dependencias desde PyPI falló por bloqueo de sockets del entorno (WinError 10013). Para continuar se copiaron distribuciones locales a ese venv, sin habilitar paquetes globales. No se afirma haber verificado una descarga desde cero ni una máquina sin dependencias disponibles. `pip check` terminó con `No broken requirements found.`

Versiones observadas: Python 3.14.7, ANTLR runtime 4.13.2, PyQt6 6.11.0, PyQt6-Qt6 6.11.2 y pytest 9.1.1. El wheel utilizado fue `sql_interpreter_files-1.0.0-py3-none-any.whl`, construido en la verificación previa. No se necesitó el repositorio Compiscript, Java ni una descarga del generador ANTLR para ejecutar el ensayo.

## Cobertura y resultados

| Área del enunciado | Evidencia observada | Resultado |
|---|---|---|
| Lexer, parser y AST | Analizar setup devolvió tokens, árbol sintáctico y AST | Aprobado |
| Análisis separado de ejecución | Analizar CREATE/INSERT sobre una base inexistente no creó el directorio | Aprobado |
| Cinco tipos y esquemas persistentes | INT, FLOAT, VARCHAR, BOOLEAN y DATE; 90 convertido a 90.0; fecha bisiesta válida y NULL conservados | Aprobado |
| CREATE/DROP TABLE e INSERT | Tres tablas principales; tabla temporal creada, poblada y eliminada | Aprobado |
| WHERE/AND/OR/ORDER BY | María/22, Ana/20, Pedro/19 en el orden esperado | Aprobado |
| INNER JOIN | Cuatro filas entre estudiantes, inscripciones y cursos, con valores exactos | Aprobado |
| Agregaciones/GROUP BY/HAVING | Curso 3: COUNT 3, SUM 255.0, AVG 85.0, MIN 70.0, MAX 95.0; curso 4 excluido por HAVING | Aprobado |
| IN y NOT IN | IN: Ana, Luis, María; NOT IN: Pedro | Aprobado |
| EXISTS y NOT EXISTS correlacionados | EXISTS: Ana, Luis, María; NOT EXISTS: Pedro | Aprobado |
| Comparación escalar | Edad máxima devuelve María | Aprobado |
| CREATE/DROP INDEX | Índice creado, utilizado, persistido y eliminado | Aprobado |
| UPDATE/INSERT/DELETE con índice vigente | Ana cambia a 21; Eva se inserta con 21 y luego se elimina; búsquedas correctas tras cada cambio | Aprobado |
| Persistencia | Un proceso nuevo recuperó Ana/21 y los grupos de inscripciones esperados | Aprobado |
| Diagnósticos y atomicidad | 14 escenarios inválidos con ubicación; hashes de todos los archivos de la base idénticos antes/después | Aprobado |
| Prevalidación escalar | Analizar subconsulta de varias filas devolvió diagnóstico sin modificar archivos | Aprobado |
| GUI instalada | 21 tokens, árbol y AST presentes; Analizar no creó base; Ejecutar mostró valor 7 | Aprobado |
| Suite completa | 144 passed in 20.27s desde el venv aislado y contra paquete instalado | Aprobado |

### Evidencia concreta del índice

Consulta: `SELECT nombre FROM estudiantes WHERE 20=edad;`. En ambos casos devolvió `Ana`.

| Métrica | Sin índice | Con índice |
|---|---:|---:|
| row_reads | 4 | 1 |
| table_scans | 1 | 0 |
| index_lookups | 0 | 1 |
| row_writes | 0 | 0 |

Después de UPDATE, buscar edad 21 devolvió Ana y buscar 20 no devolvió filas. Después de INSERT devolvió Ana y Eva; después de DELETE volvió a devolver solo Ana. Se repitió una consulta indexada con `scan` prohibido explícitamente para estudiantes: pasó con una lectura de fila, cero scans y un lookup. Esto comprueba recuperación directa, además del contador.

### Errores que se provocaron deliberadamente

Todos devolvieron código CLI 1, `accepted=false`, diagnóstico con línea/columna y ningún cambio de contenido ni archivos nuevos dentro de la base:

| Caso | Diagnóstico observado |
|---|---|
| Carácter `@` | LEXER: token recognition error |
| SELECT sin proyección | PARSER: entrada sintáctica incorrecta |
| Tabla inexistente | Tabla inexistente: inexistente |
| Columna inexistente | Columna o alias inexistente: desconocida |
| Columna ambigua en JOIN | Columna ambigua: id |
| Texto asignado a INT | Tipo incompatible en edad |
| Fecha 2023-02-29 | Fecha inválida |
| Cadena de 21 caracteres en VARCHAR(20) | VARCHAR(20) excedido en nombre |
| NULL en columna NOT NULL | La columna nombre no admite NULL |
| INSERT multirregistro con clave repetida | Restricción UNIQUE/PRIMARY KEY en id; ninguna fila parcial |
| CREATE INDEX duplicado | Índice duplicado |
| DROP INDEX inexistente | Índice inexistente |
| Escalar con dos columnas | La subconsulta requiere exactamente una columna |
| Escalar con varias filas | Subconsulta escalar retornó más de una fila |

## Evidencias conservadas

* [Registro estructurado con resultados y diagnósticos](evidence/presentation-20261031/report.json).
* [Salida de las 144 pruebas](evidence/presentation-20261031/pytest.txt).
* [Captura de resultados de la GUI instalada](evidence/presentation-20261031/gui_results.png).
* [Captura del AST en la GUI instalada](evidence/presentation-20261031/gui_ast.png).

Las capturas se inspeccionaron visualmente. Qt se ejecutó offscreen y el script cargó fuentes Windows para que el texto fuera legible en este entorno; no se modificó la aplicación para ello. No se comprobó interacción manual con una ventana nativa en un proyector: conviene ensayarla en el equipo real.

Las salidas CLI completas, SQL copiado, base de datos y logs adicionales están en `tmp/presentation-run-x9mw7yrd`. El runner de QA necesitó fijar UTF-8 explícitamente porque `-I` ignora variables PYTHON*; ese ajuste fue del script de verificación, sin cambios en la implementación SQL.

## Repetir la demostración

El venv preparado ya permite ejecutar:

```powershell
py scripts/presentation_check.py --python tmp/presentation-clean-20261031/Scripts/python.exe
.\tmp\presentation-clean-20261031\Scripts\python.exe -m sql_interpreter gui --database tmp/base-profesor-01
```

El primer comando crea otra base de ensayo única y no sobrescribe las anteriores. El segundo abre una base distinta para la demostración manual; si ya la usaron, cambien el sufijo. El guion y los resultados esperados de cada consulta están en [guia-presentacion.md](guia-presentacion.md).

Para preparar un entorno realmente descargado desde PyPI, usar los comandos normales del README en un equipo con acceso a Internet. Para reproducir la alternativa offline de este ensayo:

```powershell
py -m venv tmp/otro-venv-de-ensayo
py scripts/prepare_offline_dependencies.py tmp/otro-venv-de-ensayo/Scripts/python.exe
.\tmp\otro-venv-de-ensayo\Scripts\python.exe -m pip install --no-index --no-deps tmp/wheels/sql_interpreter_files-1.0.0-py3-none-any.whl
py scripts/presentation_check.py --python tmp/otro-venv-de-ensayo/Scripts/python.exe
```

La preparación offline requiere que las distribuciones ya existan en el Python que ejecuta el helper; no obtiene dependencias de Compiscript. El proyecto anterior conservó su único cambio local preexistente. No se hicieron commits, push ni merge.

## Valoración para la entrega

El ensayo recorrió todas las familias funcionales del documento con resultados correctos y no encontró nuevos fallos en esos escenarios. Es evidencia sólida para la presentación. No equivale a una garantía de 100 puntos ni de ausencia absoluta de errores: no hay rúbrica numérica en el documento y el docente puede utilizar otros casos.

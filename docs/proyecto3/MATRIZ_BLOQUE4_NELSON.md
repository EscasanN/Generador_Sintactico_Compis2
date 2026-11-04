# Matriz del bloque 4 de Nelson Escalante

Responsable: Nelson Escalante. Estado: **PENDIENTE** en todas las filas.
Dependencia: API completa y bloque 3 aprobado. Rúbrica: entrega funcional,
ejecución y pruebas; este bloque no absorbe los pendientes de otros.

| ID | Requisito | Caso positivo y esperado | Caso negativo o invariante | Prueba o evidencia prevista | Estado |
|---|---|---|---|---|---|
| IDE-01 | Compilar contenido actual | Buffer sin guardar muestra su propio ASM y layouts físicos. | Cambiar el archivo en disco no sustituye silenciosamente el buffer. | `tests/gui/test_mips_workflow.py::test_ide_01_unsaved_buffer` | PENDIENTE |
| IDE-02 | Exportar con seguridad | ASM UTF-8/LF idéntico al generado por API/CLI; copia y búsqueda funcionan. | Rechazo, cancelación o fallo de E/S no destruye un `.asm` existente. | `tests/gui/test_mips_workflow.py::test_ide_02_export` | PENDIENTE |
| IDE-03 | Ejecutar sin bloquear | Salida real MARS y estado visibles; se puede cancelar un proceso activo. | Tool ausente, runtime, timeout y cierre durante ejecución no dejan Java/worker vivo ni congelan Qt. | `tests/gui/test_mips_workflow.py::test_ide_03_execution_lifecycle` | PENDIENTE |
| IDE-04 | Revisión de documento | Editar/abrir/Nuevo invalida generar-ejecutar-exportar; nuevo resultado solo para revisión actual. | Señales de compilación/ejecución anterior no reemplazan el documento ni su salida vigente. | `tests/gui/test_mips_workflow.py::test_ide_04_stale_results` | PENDIENTE |
| CLI-01 | Opciones y flujos | `--emit-mips RUTA`, stdout y `--run-mips` producen los resultados documentados. | Opciones incompatibles y errores de E/S diagnosticados; rechazar ejecución con cualquiera de las exportaciones TAC/MIPS que reclame stdout, incluso combinando las tres. | `tests/test_main_mips_cli.py::test_cli_01_options` | PENDIENTE |
| CLI-02 | Estados y canales | Códigos 0/1/2; con exportación stdout contiene solo ASM, diagnósticos en stderr. | Rechazo conserva archivos existentes; error del programa y timeout no son éxito. | `tests/test_main_mips_cli.py::test_cli_02_exit_and_channels` | PENDIENTE |
| E2E-01 | Batería integral ejecutada | Cada `.cps` MIPS tiene esperado y se descubre automáticamente; resultados coinciden en API/CLI/IDE. | Falta de fixture, ID, oracle o simulador requerido impide aceptación. | `tests/mips/test_mips_fixtures.py::test_e2e_01_fixture_inventory` y ejecución parametrizada | PENDIENTE |
| DOC-01 | Instalación y defensa | Otro integrante reproduce desde checkout limpio usando README, JAR/hash y comandos registrados. | No depende de caches locales, rutas personales o archivos ignorados no descritos. | `entrega-bloque4-nelson.md`, sección instalación y ensayo, por crear | PENDIENTE |
| GIT-01 | Autoría verificable | Historial permite reconocer aportes propios de Daniel, Nadissa, Dulce y Nelson. | No commits compartidos ni autorización del profesor inventada. | Historial y referencias de las cuatro entregas; ACC-07 | PENDIENTE |

## Evidencia y comando de puerta

```powershell
py -3.14 -m pytest tests/gui/test_mips_workflow.py tests/test_main_mips_cli.py tests/mips --require-mars -q
py -3.14 -m pytest tests -q
git diff --check
```

Ejecutar Qt offscreen para automatización y repetir una demostración visible
en Windows. No confundir la prueba automática con un ensayo humano realizado.
Guardar logs/capturas fuera de los documentos y registrar rutas y resultados.

## Handoff obligatorio

- README actualizado para capacidades que realmente estén implementadas.
- Guía de instalación MARS y chequeo de dependencias, sin descarga oculta al importar.
- Evidencia de los tres componentes de la rúbrica y de las cuatro matrices.
- Ensayo de [la guía de presentación](GUIA_PRUEBAS_Y_PRESENTACION.md) desde checkout limpio.
- Auditoría con incidencias, dictamen y commit exacto; no declarar 100 % por conteo de tests solamente.

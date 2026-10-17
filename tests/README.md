# Pruebas de Compiscript

La suite cubre el frontend ANTLR, el motor semántico, la generación de código
intermedio, la CLI, la GUI y programas Compiscript completos.

## Organización

```text
tests/
├── antlr_mode/    # Gramática, caché, runtime y árbol común
├── codegen/       # IR, temporales, verificador, layouts, lowering, pipeline y fixtures
├── cps/           # Programas de la fase semántica (válidos, inválidos, advertencias)
│   └── codegen/   # Programas y TAC esperado del Proyecto 2
├── gui/           # Flujo de edición y compilación desde PyQt6
├── semantic/      # Tipos, scopes, acciones, perfiles e integración
└── test_main_cli.py
```

Inventarios ejecutables:

- Cada `.cps` de `tests/cps/` (fuera de `codegen/`) está registrado en
  `tests/semantic/test_cps_programs.py`.
- Cada `.cps` de `tests/cps/codegen/` declara sus IDs y su resultado esperado
  en la cabecera; `tests/codegen/test_codegen_fixtures.py` los descubre y
  comprueba (ver [cps/codegen/README.md](cps/codegen/README.md)).

## Ejecución

```powershell
python -m pytest tests -q
python -m pytest tests/codegen -q
python -m pytest tests/semantic -q
python -m pytest tests/gui -q
python -m pytest tests/test_main_cli.py -q
python -m pytest tests/semantic/test_cps_programs.py -vv
```

Para probar un programa manualmente:

```powershell
python -m src.main --cps tests/cps/codegen/validos/DEMO-completa.cps --emit-tac
python -m src.main --cps tests/cps/codegen/invalidos/DEMO-fallida.cps
python -m src.main --cps tests/cps/demostracion-valida.cps
```

Un programa inválido devuelve código de salida `1` porque los diagnósticos se
detectaron correctamente; `2` indica un problema de lectura o configuración.

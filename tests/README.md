# Pruebas de Compiscript

La suite cubre el frontend ANTLR, el motor semántico, la CLI, la GUI y programas
Compiscript completos.

## Organización

```text
tests/
├── antlr_mode/    # Gramática, caché, runtime y árbol común
├── cps/           # Programas válidos, inválidos y advertencias
├── gui/           # Flujo de edición y compilación desde PyQt6
├── semantic/      # Tipos, scopes, acciones, perfiles e integración
└── test_main_cli.py
```

Cada archivo `.cps` está registrado en
`tests/semantic/test_cps_programs.py`. La prueba de inventario falla si se agrega
un programa sin indicar su resultado esperado.

## Ejecución

```powershell
python -m pytest tests -q
python -m pytest tests/semantic -q
python -m pytest tests/gui -q
python -m pytest tests/semantic/test_cps_programs.py -vv
```

Para probar un programa manualmente:

```powershell
python -m src.main --cps tests/cps/demostracion-valida.cps
python -m src.main --cps tests/cps/demostracion-invalida.cps
```

El programa inválido devuelve código de salida `1` porque los diagnósticos se
detectaron correctamente.

# Programas Compiscript de demostración

Esta carpeta contiene programas `.cps` ejecutables que materializan la matriz
de cumplimiento. No son solamente ejemplos de texto: todos se compilan desde
`tests/semantic/test_cps_programs.py` con la gramática y el perfil semántico de
entrega.

## Organización

| Ruta | Resultado esperado | Uso |
|---|---|---|
| `demostracion-valida.cps` | `ACCEPT` | Presentación integral del flujo correcto. |
| `demostracion-invalida.cps` | `REJECT` | Muestra errores `type`, `scope`, `function`, `control_flow`, `class` y `array` juntos. |
| `validos/` | `ACCEPT` | Un programa por cada regla TYP, SCP, FUN, CTL, CLS, LST y GEN. |
| `invalidos/` | `REJECT` | Contraejemplos aislados con categoría verificable. |
| `advertencias/` | `ACCEPT` con warning | Código inalcanzable detectado sin convertirlo en error. |

Los prefijos de archivo corresponden directamente a
`docs/phase3/MATRIZ_CUMPLIMIENTO.md`. `CTL-04`, `CLS-04` y `EXT-*` cubren el
endurecimiento adicional: `catch`, herencia, `foreach`, constructor implícito,
concatenación, módulo y referencias nulas.

## Ejecución rápida

Desde la raíz del repositorio:

```powershell
python -m src.main --cps tests/cps/demostracion-valida.cps
python -m src.main --cps tests/cps/demostracion-invalida.cps
python -m pytest tests/semantic/test_cps_programs.py -q
```

El segundo comando debe terminar en `REJECT` y devolver código de salida `1`;
eso demuestra que los diagnósticos esperados fueron detectados, no que el
analizador haya fallado internamente.

Para una demostración puntual puede abrirse cualquier archivo desde la GUI o
pasarlo al comando `--cps`. Los comentarios al inicio de cada archivo explican
la regla que ejercita y por qué debe aceptarse o rechazarse.

# Programas de generación de código intermedio (Proyecto 2)

Batería ejecutable de la fase de TAC. La prueba
`tests/codegen/test_codegen_fixtures.py` compila cada archivo con
`compile_compiscript` y comprueba el resultado que declara su cabecera.

## Organización

| Ruta | Resultado | Uso |
|---|---|---|
| `validos/` | `ACCEPT` | Un programa por dominio de la matriz (EXP, CTL, FUN, CLS, LST, TMP, EXT) y `DEMO-completa.cps`. |
| `invalidos/` | `REJECT` | Al menos un caso por fase que falla: `syntax`, `semantic` y `codegen`, y `DEMO-fallida.cps`. |
| `esperados/` | TAC golden | TAC aprobado de programas representativos; mismo nombre que su `.cps` en `validos/`. |

## Cabecera obligatoria

```text
// IDs: FUN-07, FUN-08, FUN-09
// Esperado: ACCEPT
```

```text
// IDs: PIPE-04, EXT-08
// Esperado: REJECT codegen IRGEN-UNSUPPORTED-NODE
```

- `IDs` enumera los requisitos de `docs/proyecto2/MATRIZ_CUMPLIMIENTO.md` que
  el programa demuestra. La prueba exige que los válidos cubran todos los IDs
  obligatorios de expresiones, control, funciones, clases, listas, temporales y
  extensiones.
- `Esperado` es `ACCEPT` o `REJECT <fase> [código]`. En un rechazo se verifica
  la fase, que existan diagnósticos y que no haya TAC; en `codegen` se verifica
  además el código del diagnóstico IR.

## Golden TAC

Los `.tac` se reservan para casos representativos; el resto se valida sobre la
IR estructurada para que un cambio de formato no rompa toda la suite. Si un
cambio del generador es intencional, se revisa el diff y se regenera con la CLI:

```powershell
python -m src.main --cps tests/cps/codegen/validos/DEMO-completa.cps --emit-tac tests/cps/codegen/esperados/DEMO-completa.tac
```

## Ejecución

```powershell
python -m pytest tests/codegen/test_codegen_fixtures.py -v
python -m src.main --cps tests/cps/codegen/validos/DEMO-completa.cps --emit-tac
python -m src.main --cps tests/cps/codegen/invalidos/DEMO-fallida.cps
```

El segundo programa termina con `REJECT` y código de salida `1`.

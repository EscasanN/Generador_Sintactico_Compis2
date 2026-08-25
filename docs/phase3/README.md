# Fase 3 — Análisis semántico de Compiscript

## Estado actual

La Fase 3 está en **planificación**. Existe únicamente el scaffold de carpetas descrito abajo; todavía no existen el parser ANTLR de Compiscript, el analizador semántico, la tabla de símbolos de esta fase ni sus pruebas automatizadas.

La base sobre la que se trabajará es la rama `feature/fase3-compiscript`, creada desde `origin/feature/gui-enhancement` en el commit `6309ef4`.

El profesor autorizó que el equipo esté formado por cuatro integrantes.

## Scaffold disponible

```text
src/
├── compiscript/
│   ├── grammar/
│   └── generated/
└── semantic/

tests/
└── semantic/
    └── fixtures/
```

Cada carpeta nueva contiene únicamente un `.gitkeep`. Al agregar el primer archivo real a una carpeta, su `.gitkeep` puede eliminarse en el mismo commit.

## Documentos

- [Gramática ANTLR de Compiscript](../../src/compiscript/grammar/Compiscript.g4)
- [Especificación del lenguaje](../compiscript/ESPECIFICACION.md)
- [Plan de implementación](PLAN.md)
- [Arquitectura propuesta](ARQUITECTURA.md)
- [División del trabajo](DIVISION_TRABAJO.md)
- [Reglas y decisiones pendientes](REGLAS_Y_DECISIONES.md)

## Fuentes de verdad

Cuando dos documentos se contradigan, se seguirá este orden:

1. Instrucciones escritas o correcciones del profesor.
2. Enunciado oficial del proyecto.
3. Gramática oficial de Compiscript entregada por el curso.
4. Decisiones internas documentadas por el equipo.

Los ejemplos creados por el equipo nunca deben considerarse una especificación oficial.

## Regla de documentación

Cada documento debe indicar el estado real del proyecto. Una sección propuesta debe usar expresiones como “por implementar” o “arquitectura objetivo”; no debe describir archivos futuros como si ya existieran.

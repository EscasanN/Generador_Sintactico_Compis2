# Fase 3 — Modo ANTLR y análisis semántico

## Estado actual

La rama base es `feature/fase3-compiscript`, creada desde
`origin/feature/gui-enhancement`. El profesor autorizó un equipo de cuatro
integrantes.

El IDE conserva el flujo YALex + YAPar e incorpora un segundo modo que:

- abre gramáticas ANTLR combinadas `.g4`;
- descubre sus reglas sintácticas;
- permite elegir la regla inicial;
- genera Lexer, Parser y Visitor Python en `output/antlr/`;
- reutiliza la generación mediante caché por hash;
- analiza una entrada completa;
- muestra tokens, árbol y diagnósticos.

El análisis semántico y la tabla de símbolos de esta fase todavía están
pendientes.

`Compiscript.g4` es una gramática de ejemplo. Debe funcionar como entrada, pero
el motor no puede depender de sus nombres ni requerir cambios Python cuando se
cargue otra gramática.

## Modos del IDE

| Modo | Entradas | Resultados |
|---|---|---|
| YALex + YAPar | `.yal`, `.yapar`, entrada | NFA, DFA, LR(0), SLR, LALR, LL(1), pasos y árboles |
| ANTLR | `.g4`, regla inicial, entrada | tokens, árbol y diagnósticos ANTLR |

Los resultados propios de YAPar no se atribuyen a ANTLR ni se eliminan.

## Documentos

- [Gramática ANTLR de ejemplo](../../src/compiscript/grammar/Compiscript.g4)
- [Especificación de referencia](../compiscript/ESPECIFICACION.md)
- [Plan de implementación](PLAN.md)
- [Arquitectura](ARQUITECTURA.md)
- [División resumida](DIVISION_TRABAJO.md)
- [Guía detallada por integrante](GUIA_IMPLEMENTACION_POR_INTEGRANTE.md)
- [Reglas y decisiones pendientes](REGLAS_Y_DECISIONES.md)

## Fuentes de verdad

1. Instrucciones o correcciones escritas del profesor.
2. Enunciado oficial.
3. Requisitos confirmados de entrada y evaluación.
4. Gramáticas entregadas, tratadas como datos de entrada.
5. Decisiones internas documentadas.

Ninguna gramática de ejemplo debe convertirse en lógica codificada dentro del
motor.

## Regla de documentación

Los documentos deben distinguir capacidades implementadas, pendientes y
opcionales. Una prueba con Compiscript no significa que el motor sea exclusivo
de Compiscript.

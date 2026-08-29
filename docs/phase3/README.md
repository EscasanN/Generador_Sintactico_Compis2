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

- [Enunciado oficial del Proyecto 2](../../Generador_de_Analizadores_Semánticos.pdf)
- [Gramática ANTLR de ejemplo](../../src/compiscript/grammar/Compiscript.g4)
- [Especificación de referencia](../compiscript/ESPECIFICACION.md)
- [Matriz de cumplimiento y pruebas](MATRIZ_CUMPLIMIENTO.md)
- [Plan de implementación](PLAN.md)
- [Arquitectura](ARQUITECTURA.md)
- [División resumida](DIVISION_TRABAJO.md)
- [Guía detallada por integrante](GUIA_IMPLEMENTACION_POR_INTEGRANTE.md)
- [Reglas y decisiones pendientes](REGLAS_Y_DECISIONES.md)

## Fuentes de verdad

1. Instrucciones o correcciones escritas del profesor.
2. `Generador_de_Analizadores_Semánticos.pdf`.
3. Requisitos confirmados de entrada y evaluación.
4. Gramáticas entregadas, tratadas como datos de entrada.
5. Decisiones internas documentadas.

Ninguna gramática de ejemplo debe convertirse en lógica codificada dentro del
motor.

## Secuencia de trabajo del equipo

La implementación restante se divide en bloques consecutivos:

| Orden | Responsable | Entrega cerrada |
|---:|---|---|
| 1 | Daniel | Diagnósticos, tipos, valores y expresiones |
| 2 | Nadissa | Símbolos, perfiles, acciones y evaluador |
| 3 | Dulce | Adaptador ANTLR-semántica y prueba con otra gramática |
| 4 | Nelson | Perfil Compiscript, IDE semántico y entrega final |

Cada rama parte de la integración del bloque anterior. Una persona termina su
implementación y pruebas antes de entregar; no regresa a programar en un bloque
posterior. La [división resumida](DIVISION_TRABAJO.md) contiene las puertas de
aceptación y la [guía detallada](GUIA_IMPLEMENTACION_POR_INTEGRANTE.md) define
archivos, clases y funciones.

## Flujo final exigido

```text
gramática oficial .g4
        ↓ genera
Lexer + Parser de ANTLR
        ↓ procesan
archivo fuente .cps
        ↓
árbol sintáctico visual
        ↓ ParseTreeWalker + Listener, o Visitor
diagnósticos semánticos + tabla de símbolos
```

El IDE debe permitir crear, abrir, editar y guardar `.cps`, además de compilar
todo su contenido. **ACCEPT** significa que no existen errores léxicos,
sintácticos ni semánticos.

La [matriz de cumplimiento](MATRIZ_CUMPLIMIENTO.md) traduce cada requisito del
PDF a una prueba localizable. MiniCalc demuestra generalidad, pero la evaluación
se realiza sobre Compiscript y la gramática oficial disponible.

## Regla de documentación

Los documentos deben distinguir capacidades implementadas, pendientes y
opcionales. Una prueba con Compiscript no significa que el motor sea exclusivo
de Compiscript.

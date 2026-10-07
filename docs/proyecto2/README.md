# Planificación del Proyecto 2 — código intermedio

Esta carpeta contiene la planificación de la siguiente etapa de Compiscript:
generar código de tres direcciones (TAC) a partir del árbol sintáctico y de la
tabla de símbolos producidos por la entrega semántica.

> Estado: estos documentos describen trabajo propuesto. Las casillas sin marcar
> no representan funcionalidades ya implementadas.

La fuente oficial es
[proyecto2-compiladores.md](proyecto2-compiladores.md). La propuesta también
incorpora los apuntes del curso sobre generación de código intermedio y
entornos en tiempo de ejecución, especialmente TAC, cuádruplos, reciclaje de
temporales, offsets y registros de activación.

## Orden recomendado de lectura

| Documento | Propósito |
|---|---|
| [PLAN.md](PLAN.md) | Secuencia completa de implementación, puertas y riesgos. |
| [DIVISION_TRABAJO.md](DIVISION_TRABAJO.md) | Responsabilidad de cada integrante, ramas y entregables. |
| [GUIA_IMPLEMENTACION_POR_INTEGRANTE.md](GUIA_IMPLEMENTACION_POR_INTEGRANTE.md) | Archivos, APIs y pruebas esperadas por bloque. |
| [ARQUITECTURA.md](ARQUITECTURA.md) | Flujo técnico propuesto y contratos entre fases. |
| [DISENO_TAC.md](DISENO_TAC.md) | Lenguaje intermedio, instrucciones, temporales y ejemplos de traducción. |
| [MATRIZ_CUMPLIMIENTO.md](MATRIZ_CUMPLIMIENTO.md) | Trazabilidad entre el enunciado, pruebas y responsables. |
| [REGLAS_Y_DECISIONES.md](REGLAS_Y_DECISIONES.md) | Decisiones adoptadas, supuestos y preguntas para el profesor. |

## Decisiones de alcance

- Se reutilizan Compiscript.g4, ANTLR, el perfil semántico y la tabla de
  símbolos existentes.
- La API semántica actual se conserva. Una nueva función de compilación
  coordina sintaxis, semántica y generación de TAC.
- El TAC se representa internamente mediante cuádruplos tipados y se muestra en
  un formato textual legible.
- La generación se detiene si hay errores léxicos, sintácticos o semánticos.
  Los warnings no impiden producir TAC.
- El plan cubre primero el mínimo oficial y después las construcciones
  adicionales ya aceptadas por la gramática actual.
- No forman parte de esta entrega la optimización global, SSA, código
  ensamblador, asignación de registros físicos ni recolección de basura.

## Flujo esperado

~~~text
programa.cps
    ↓
ANTLR + Compiscript.g4
    ↓
árbol sintáctico común
    ↓
análisis semántico + tabla de símbolos
    ↓ solo si no hay errores
anotaciones semánticas + layout de símbolos y frames
    ↓
generador TAC
    ↓
verificador de IR
    ↓
TAC textual + tabla extendida + diagnósticos
    ↓
CLI o IDE
~~~

## Base de trabajo

La rama base prevista es **refactor/compiscript-only**, que contiene únicamente
el flujo vigente de Compiscript. La entrega semántica original permanece
resguardada por la etiqueta **entrega-semantica-100** y no debe reescribirse.

Antes de comenzar el primer bloque se debe crear una rama de integración para
el proyecto y confirmar que la suite actual pasa sin cambios.

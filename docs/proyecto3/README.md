# Planificación de la fase 3 de Compiscript

Esta entrega agrega generación y ejecución de MIPS al compilador Compiscript.
La meta es cubrir la rúbrica completa y conservar las construcciones que ya
acepta el Proyecto 2. El simulador acordado es **MARS 4.5**.

**Estado: bloques 1, 3 y 4 aprobados; bloque 2 implementado (dictamen pendiente).**
El núcleo de Daniel, las llamadas, entornos y closures de Nadissa y el runtime completo
con el pipeline `.cps` → MIPS de Dulce se ejecutan en MARS (`compile_to_mips`). El
bloque 4 los presenta en la CLI y el IDE; ver [su entrega](entrega-bloque4-nelson.md).
La rama integrada es `feature/proyecto3-mips` (revisión en `fix/proyecto3-final-compliance`): 1267 pruebas aprobadas con MARS
obligatorio. Ver [la auditoría contra el enunciado](AUDITORIA_FINAL.md).

Ver [entrega del bloque 1](entrega-bloque1-daniel.md): 985 pruebas aprobadas
con MARS obligatorio, 80 nuevas y un ejemplo ejecutable para el siguiente integrante.
Ver [entrega del bloque 2](entrega-bloque2-nadissa.md): 1051 pruebas aprobadas con
MARS obligatorio (66 nuevas): ABI, recursión, closures escapadas y métodos ligados.
Las [incidencias del bloque 1](entrega-bloque1-daniel.md#incidencias-tras-la-entrega) ya están
corregidas sobre esta rama: 1072 pruebas aprobadas con MARS obligatorio (21 nuevas).
Ver [entrega del bloque 3](entrega-bloque3-dulce.md): cadenas, listas, objetos, excepciones,
`generate_mips` y `compile_to_mips`, con 17 fixtures `.cps` ejecutados en MARS.

La fuente de requisitos es [Proyecto_Fase3_Compiladores.md](../../Proyecto_Fase3_Compiladores.md).
La carpeta histórica [docs/phase3](../phase3/README.md) corresponde al análisis
semántico; esta carpeta corresponde a la nueva entrega de generación MIPS.

## Flujo de implementación

```text
Base Proyecto 2 aceptada
  → Daniel: núcleo MIPS, registros y simulador
  → Nadissa: activaciones, llamadas y entornos
  → Dulce: runtime completo y pipeline .cps → MIPS
  → Nelson: IDE, CLI, fixtures integrales y entrega
  → aceptación del equipo
```

Cada integrante entrega código, pruebas y documentación antes del siguiente.
La evidencia son ejecuciones con resultados esperados, además de comprobaciones
de invariantes; un archivo ensamblador por sí solo no demuestra cumplimiento.

## Documentos de trabajo

| Documento | Uso |
|---|---|
| [PLAN.md](PLAN.md) | Secuencia, precondiciones y puertas de aceptación. |
| [DIVISION_TRABAJO.md](DIVISION_TRABAJO.md) | Propiedad, ramas y contribuciones individuales. |
| [ARQUITECTURA.md](ARQUITECTURA.md) | APIs, resultados, dependencias y flujo de datos. |
| [DISENO_MIPS.md](DISENO_MIPS.md) | Máquina destino, ABI, registros, memoria y catálogo TAC. |
| [REGLAS_Y_DECISIONES.md](REGLAS_Y_DECISIONES.md) | Requisitos oficiales, acuerdos y confirmaciones externas. |
| [GUIA_IMPLEMENTACION_POR_INTEGRANTE.md](GUIA_IMPLEMENTACION_POR_INTEGRANTE.md) | Módulos, contratos y estrategia por bloque. |
| [MATRIZ_CUMPLIMIENTO.md](MATRIZ_CUMPLIMIENTO.md) | Rúbrica y condiciones globales de aceptación. |
| [MATRIZ_BLOQUE1_DANIEL.md](MATRIZ_BLOQUE1_DANIEL.md) | Núcleo, registros, números y simulador. |
| [MATRIZ_BLOQUE2_NADISSA.md](MATRIZ_BLOQUE2_NADISSA.md) | ABI, llamadas, closures y métodos ligados. |
| [entrega-bloque2-nadissa.md](entrega-bloque2-nadissa.md) | Handoff, evidencia y reproducción del bloque 2. |
| [MATRIZ_BLOQUE3_DULCE.md](MATRIZ_BLOQUE3_DULCE.md) | Runtime, objetos, listas, excepciones y pipeline. |
| [entrega-bloque3-dulce.md](entrega-bloque3-dulce.md) | Handoff, evidencia, incidencias y reproducción del bloque 3. |
| [MATRIZ_BLOQUE4_NELSON.md](MATRIZ_BLOQUE4_NELSON.md) | IDE, CLI y entrega reproducible. |
| [entrega-bloque4-nelson.md](entrega-bloque4-nelson.md) | Handoff, evidencia, instalación, ensayo e incidencias del bloque 4. |
| [GUIA_PRUEBAS_Y_PRESENTACION.md](GUIA_PRUEBAS_Y_PRESENTACION.md) | Casos, comandos de aceptación y demostración. |
| [PLANTILLA_ENTREGA_BLOQUE.md](PLANTILLA_ENTREGA_BLOQUE.md) | Evidencia que debe registrar cada responsable. |
| [AUDITORIA_FINAL.md](AUDITORIA_FINAL.md) | Estado de integración y cierre de la entrega. |

## Puntos que deciden la entrega

La rúbrica asigna 20 puntos a llamadas/retornos, 20 a registros/pila y 60 a
MIPS ejecutable con pruebas. La matriz global vincula estos tres componentes
con los cuatro bloques; los bloques no representan cuatro notas independientes.

La entrega requiere una base sin fallos no explicados, todas las matrices
aprobadas, ejecución real en MARS, regresión completa, IDE funcional,
documentación reproducible y commits propios de los cuatro integrantes.
La evidencia permite comprobar estos criterios; la nota la determina la evaluación.

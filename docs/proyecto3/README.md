# Planificación de la fase 3 de Compiscript

Esta entrega agrega generación y ejecución de MIPS al compilador Compiscript.
La meta es cubrir la rúbrica completa y conservar las construcciones que ya
acepta el Proyecto 2. El simulador acordado es **MARS 4.5**.

**Estado: bloque 1 aprobado; bloque 2 implementado (revisión pendiente); bloques 3 y 4 pendientes.**
El núcleo de Daniel y las llamadas, entornos y closures de Nadissa se ejecutan con IR
manual y MARS; el pipeline completo `.cps` → MIPS y su IDE corresponden a los bloques
3 y 4. Los comandos de esas etapas siguen siendo objetivos de implementación.

Ver [entrega del bloque 1](entrega-bloque1-daniel.md): 985 pruebas aprobadas
con MARS obligatorio, 80 nuevas y un ejemplo ejecutable para el siguiente integrante.
Ver [entrega del bloque 2](entrega-bloque2-nadissa.md): 1050 pruebas aprobadas con
MARS obligatorio (65 nuevas): ABI, recursión, closures escapadas y métodos ligados.

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
| [MATRIZ_BLOQUE4_NELSON.md](MATRIZ_BLOQUE4_NELSON.md) | IDE, CLI y entrega reproducible. |
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

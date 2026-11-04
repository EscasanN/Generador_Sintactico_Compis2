# División del trabajo de generación MIPS

## Dependencias y propiedad

| Orden | Integrante | Responsabilidad principal | Rama propuesta |
|---:|---|---|---|
| 1 | Daniel Chet | Núcleo, emisor, registros, escalares y MARS | `feature/proyecto3-01-mips-core` |
| 2 | Nadissa Vela | Layouts, activaciones, llamadas, entornos y closures | `feature/proyecto3-02-calls-environments` |
| 3 | Dulce Ambrosio | Runtime completo, memoria compuesta, excepciones y pipeline | `feature/proyecto3-03-runtime-pipeline` |
| 4 | Nelson Escalante | IDE, CLI, fixtures integrales y entrega | `feature/proyecto3-04-ide-delivery` |

Las ramas son secuenciales; no se crean las cuatro desde la misma base.
La integración final propuesta es `feature/proyecto3-mips`.

## Entrega individual

Cada integrante debe aportar commits propios de implementación, pruebas de
comportamiento y documentación. Puede separar esos cambios en varios commits
coherentes; no debe crear commits vacíos para simular contribución.

Su handoff contiene los IDs de su matriz, APIs, casos ejecutados en MARS,
comandos, resultados, commit exacto, limitaciones y dictamen de la puerta.
Se utilizará [PLANTILLA_ENTREGA_BLOQUE.md](PLANTILLA_ENTREGA_BLOQUE.md).

## Límites entre bloques

| Frontera | Acuerdo |
|---|---|
| Daniel → Nadissa | Emisor extensible y protocolo de ubicación/llamadas congelados; el bloque 1 se verifica con IR escalar manual. |
| Nadissa → Dulce | ABI y closures funcionan sin runtime compuesto; heap e impresión mínimos ya existen. |
| Dulce → Nelson | API `.cps` → MIPS y ejecución por adaptador disponibles; CLI e IDE solo presentan y coordinan. |
| Nelson → equipo | Evidencia reproducible e integración; no debe completar silenciosamente funciones pendientes de otros. |

Daniel es propietario de `models`, `diagnostics`, `emitter`, `registers`,
`scalar`, `runtime_base` y `simulator` dentro del paquete MIPS.
Nadissa es propietaria de `layout`, `calls` y `environments`.
Dulce es propietaria de `runtime`, `objects`, `lists`, `exceptions`,
`generator` y `pipeline`. Nelson modifica los consumidores CLI/Qt y la guía
principal. La guía de implementación establece los nombres de pruebas.

Los módulos de contratos del bloque 1 no importan implementaciones futuras.
Los handlers de los bloques 2 y 3 se componen en el generador integral del
bloque 3; esto evita que el autor del núcleo deba regresar a enlazarlos.

## Revisión y contribución

Antes de integrar, otro integrante revisa el diff y reproduce la puerta.
Una fila aprobada debe tener prueba versionada y evidencia del commit revisado.
Los logs pueden guardarse en `output/qa/proyecto3/`, pero sus comandos,
resultados y commits se resumen en la entrega versionada.

El bloque 1 contribuye especialmente a los 20 puntos de registros; el bloque 2
a los 20 de llamadas. Los 60 puntos de generación funcional involucran a los
cuatro. La distribución no asigna 25 puntos individuales a cada persona.

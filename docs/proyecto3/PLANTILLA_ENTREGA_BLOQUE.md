# Plantilla de entrega de un bloque MIPS

Copiar al cerrar un bloque, reemplazar los campos y conservar solo evidencia
real. No marcar APROBADO por tener una implementación sin sus pruebas.

## Identificación

| Campo | Valor por completar |
|---|---|
| Bloque e integrante | PENDIENTE |
| Fecha y rama | PENDIENTE |
| Commit base aceptado | PENDIENTE |
| Commit implementado y revisado | PENDIENTE |
| Revisor de la puerta | PENDIENTE |
| Python / Java / MARS y SHA-256 JAR | PENDIENTE |

## Cambios y contratos

Describir el comportamiento entregado, módulos propios, APIs públicas y
dependencias. Vincular la matriz individual. Explicar cualquier desviación
del diseño y registrar quién la aprobó y qué pruebas la cubren.

## Evidencia por requisito

Una fila por cada ID de la matriz del integrante; agregar filas si corresponde.

| ID | Requisito | Responsable | Prueba positiva y fixture | Negativa o invariante | Esperado | Comando | Resultado real / log | Commit | Estado |
|---|---|---|---|---|---|---|---|---|---|
| PENDIENTE | PENDIENTE | PENDIENTE | PENDIENTE | PENDIENTE | PENDIENTE | PENDIENTE | PENDIENTE | PENDIENTE | PENDIENTE |

Para ejecutar en MARS, registrar stdout, salida y estado, además del nombre de
la prueba. Si el caso negativo espera un error, registrar su código exacto.

## Regresión y reproducción

Incluir comandos copiados de la ejecución, número real de pruebas y skips,
duración, entorno y resultado. Indicar si se usó checkout limpio o caches.
Los logs locales ignorados se resumen en esta entrega; no serán su única evidencia.

## Incidencias

Por incidencia: ID, gravedad, reproducción, responsable, impacto y estado.
Una incidencia bloqueante deja la puerta pendiente. No ocultar fallos con
`skip`, `xfail` o modificación del oracle sin justificación del comportamiento.

## Puerta de aceptación

- [ ] Todos los IDs propios tienen evidencia y están aprobados.
- [ ] MARS real ejecutó los casos exigidos sin skips por dependencia.
- [ ] Regresión acumulada y formato del diff correctos.
- [ ] Contratos utilizables por el siguiente bloque sin implementar pendientes propios.
- [ ] Otro integrante reprodujo la puerta y registró dictamen.
- [ ] Commits de autoría individual identificables y documentación actualizada.

Dictamen: **PENDIENTE**. Cambiar a APROBADO solo con fecha, commit y revisor.

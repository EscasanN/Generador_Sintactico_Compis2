# Auditoría de integración y entrega MIPS

**Estado de integración global: PENDIENTE.** El bloque 1 de Daniel está
aprobado con evidencia en [su entrega](entrega-bloque1-daniel.md): 985 pruebas
aprobadas con MARS obligatorio, 80 nuevas. Esta página conserva el cierre global
que se completará después de los cuatro bloques; no declara funcional el
compilador MIPS completo.

## Registro del cierre

| Dato | Resultado |
|---|---|
| Commit de integración evaluado | PENDIENTE |
| Entregas individuales y revisiones | PENDIENTE |
| Python / Java / MARS y SHA-256 del JAR | PENDIENTE |
| Comandos de aceptación y logs | PENDIENTE |
| Regresión previa y suite MIPS requerida | PENDIENTE |
| Ensayo visible de IDE y MARS | PENDIENTE |
| Checkout limpio repetido por otro integrante | PENDIENTE |
| Incidencias y dictamen final | PENDIENTE |

## Lista de aceptación del equipo

- [ ] Puertas de Daniel, Nadissa, Dulce y Nelson aprobadas sobre commits identificados.
- [ ] Todos los IDs y ACC-01 a ACC-08 con evidencia localizable.
- [ ] Rúbrica 20/20/60 vinculada a comportamiento ejecutado, no solo diseño.
- [ ] Todos los opcodes y capacidades acordadas cubiertos; ninguna omisión silenciosa.
- [ ] Llamadas, recursión, registros vivos y spills verificados con canarios.
- [ ] Closures, herencia local y excepciones entre frames ejecutadas en MARS.
- [ ] Casos de error con fase/código correctos y sin salidas parciales aceptadas.
- [ ] CLI/IDE coherentes, exportación segura y resultados vigentes por revisión.
- [ ] MARS requerido disponible; cero skips de integración en aceptación.
- [ ] Suite previa limpia y gramática/perfil preservados.
- [ ] Instalación y demostración repetidas desde checkout limpio.
- [ ] Aportes individuales, autorización de cuatro integrantes y enunciado disponibles.

## Interpretación del dictamen

Marcar listo solo cuando no queden bloqueos dentro del alcance acordado.
Las observaciones cosméticas pueden quedar identificadas como tales, con
responsable y justificación. Cualquier cambio funcional posterior invalida
las pruebas afectadas hasta repetirlas.

La revisión inicial de la base del Proyecto 2 tuvo 903 pruebas aprobadas y
dos fallos del fixture local de listas; consta en [PLAN.md](PLAN.md). No
trasladar ese resultado a la nueva fase ni afirmar una suite limpia sin repetirla.

La corrección `f2f2a15` restauró el fixture con autorización del propietario.
La base volvió a pasar 905 pruebas antes del desarrollo. El código completo
del bloque 1 hasta `f580a20` pasó 985 pruebas, incluidas las de MARS, como
registra su entrega; las puertas restantes permanecen pendientes.

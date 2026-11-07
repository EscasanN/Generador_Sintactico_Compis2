# Plan de implementación de la fase 3

## Objetivo

Traducir el IR estructurado del Proyecto 2 a MIPS32 ejecutable en MARS 4.5,
preservando el frontend, el TAC y las capacidades actuales de Compiscript.
El alcance incluye flotantes, cadenas, closures, clases, herencia local,
listas y excepciones; no se acepta omitirlas silenciosamente.

## Base y puerta de entrada

Base inspeccionada: `feature/proyecto2-codegen`, commit `6791fef`.
La etiqueta `entrega-semantica-100` conserva la entrega semántica.
La rama de integración propuesta es `feature/proyecto3-mips`.

- [x] Restaurar el fixture completo de listas con autorización del propietario, conservando su golden: `f2f2a15`.
- [x] Enunciado raíz incluido en la base publicada `82756c9`.
- [x] Ejecutar regresión limpia antes de implementar: 905 pruebas aprobadas.
- [ ] Confirmar gramática/perfil compatibles y conservar sus APIs y fingerprint.
- [ ] Registrar autorización para cuatro integrantes en esta entrega; el enunciado indica tres.
- [x] Obtener MARS 4.5 y registrar procedencia/hash en la entrega de Daniel.
- [x] Congelar diseño y contratos del bloque 1 tras implementación y revisión técnica.

La revisión inicial ejecutó 905 pruebas: 903 aprobadas y dos fallos asociados
al fixture local reducido. Su versión de Git satisface ambas comprobaciones.
Este resultado histórico **no es una aceptación limpia de la nueva fase**.

## Bloques secuenciales

### 1. Daniel Chet

- [x] Implementar modelos, diagnósticos, emisor y etiquetas MIPS deterministas.
- [x] Congelar protocolos de layout, llamadas y registro de handlers de opcodes.
- [x] Implementar `getReg()`, banco flotante, respaldos, derrames y barreras.
- [x] Traducir escalares, conversiones, saltos y `RELEASE`.
- [x] Implementar auxiliares mínimos de heap, impresión escalar y terminación.
- [x] Implementar adaptador MARS con ensamblado, ejecución y límites.
- [x] Completar [su matriz](MATRIZ_BLOQUE1_DANIEL.md) y [el handoff](entrega-bloque1-daniel.md).

**Puerta 1:** IR de prueba ejecutada en MARS con números, ramas, bucles y
derrames forzados; interfaces de los siguientes bloques documentadas y estables.
No necesita el pipeline `.cps` nuevo para cerrar.

### 2. Nadissa Vela

- [x] Construir layouts físicos por identidad de símbolo y por procedimiento.
- [x] Implementar argumentos, prólogos, epílogos y retorno único.
- [x] Probar llamadas directas, indirectas, recursión y valores vivos.
- [x] Implementar entornos, closures escapadas y métodos ligados, incluidos auxiliares de heap propios.
- [x] Cubrir capturas compartidas y enlace léxico a varios niveles.
- [x] Completar [su matriz](MATRIZ_BLOQUE2_NADISSA.md) y [el handoff](entrega-bloque2-nadissa.md); falta la revisión independiente de la puerta (revision realizada por Dulce previo a desarrollar).

**Puerta 2:** llamadas y closures verificadas en MARS con IR manual tipada,
sin depender de que existan listas, objetos completos o excepciones del bloque 3.
Los receptores de prueba pueden ser regiones de memoria preparadas por el harness.

### 3. Dulce Ambrosio

- [ ] Implementar cadenas, listas, objetos, herencia e inicializadores.
- [ ] Completar runtime de errores y desenrollado de excepciones.
- [ ] Integrar todo el catálogo de opcodes y las llamadas externas permitidas.
- [ ] Implementar generación integral y `compile_to_mips` conservando las APIs previas.
- [ ] Probar `.cps` por dominio con salida esperada y rechazo por fase.
- [ ] Completar [su matriz](MATRIZ_BLOQUE3_DULCE.md) y el handoff.

**Puerta 3:** todos los opcodes emitidos por el compilador tienen traducción
y evidencia; programas `.cps` completos se ejecutan por la API Python en MARS.

### 4. Nelson Escalante

- [ ] Integrar generación y ejecución explícita en IDE y CLI.
- [ ] Mostrar/exportar `.asm`, salida, errores, estado y layouts MIPS físicos.
- [ ] Conservar seguridad del documento, invalidación de resultados y workers Qt.
- [ ] Consolidar fixtures, oráculos, instalación y guías de defensa.
- [ ] Ejecutar desde checkout limpio y completar [su matriz](MATRIZ_BLOQUE4_NELSON.md).
- [ ] Registrar aceptación conjunta en [AUDITORIA_FINAL.md](AUDITORIA_FINAL.md).

**Puerta 4:** demostración reproducible desde una ventana y desde CLI,
regresión completa aprobada y todos los registros de evidencia completos.

## Integración y cambios de contrato

Cada rama se crea desde la integración aceptada de la anterior. Antes de cerrar
un bloque se revisan sus APIs, pruebas, documentación y casos de error.
Una deficiencia del contrato se corrige en la puerta de su propietario, no se
deja como tarea implícita para el último integrante. Si se descubre después,
se registra incidencia, propietario, impacto y nueva regresión; se reabre la
puerta afectada y se repiten las comprobaciones dependientes.

El equipo revisa cada entrega antes de integrarla. No se reescribe la autoría
ni se crean commits conjuntos. La auditoría final verifica integración;
no reemplaza los entregables de los bloques.

## Riesgos y respuesta

| Riesgo | Respuesta exigida |
|---|---|
| Mezclar direcciones MIPS32 con slots abstractos de ocho bytes | Descriptor físico explícito y pruebas de alineación, offsets y padding. |
| Perder valores en llamadas, joins o helpers | Barreras conservadoras y pruebas con pocos registros disponibles. |
| Closure sobre frame ya terminado | Entorno en heap y prueba de escape ejecutada. |
| Falso éxito al omitir un opcode | Catálogo exhaustivo, cobertura del enum y diagnóstico de unsupported. |
| Error runtime que salta al catch equivocado | Manejadores enlazados y pruebas entre varios frames. |
| Simulador ausente convertido en skip | Modo de aceptación exige MARS; ausencia hace fallar el comando. |
| Sobrecargar al bloque 4 | Pruebas y documentación pertenecen al bloque que implementa la funcionalidad. |

No se incluyen optimización global, SSA, ABI de Linux, hardware real,
recolección de basura ni compatibilidad con varios simuladores como requisitos.

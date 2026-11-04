# Reglas y decisiones de la fase 3

## Requisitos del enunciado

| Tema | Requisito oficial |
|---|---|
| Entrada y salida | `.cps`, ensamblador MIPS y errores de compilación. |
| Traducción | Partir del análisis semántico y TAC existentes. |
| Procedimientos | Llamadas, retorno, parámetros, valor de retorno y preservación de memoria con `$sp`. |
| Registros | `getReg()` o uso de pila; resolver falta de registros y respetar clases de registros. |
| Validación | Ejecutar el código en un simulador MIPS y comprobar su funcionamiento. |
| Pruebas | Casos exitosos y fallidos presentes y funcionales en la evaluación. |
| IDE | Escribir y compilar Compiscript. |
| Git | Commits individuales; no commits compartidos. |
| Documentación | Arquitectura, organización y ejecución. |
| Evaluación | Llamadas 20, registros/pila 20, MIPS y pruebas 60; debe funcionar el día de presentación. |
| Modalidad escrita | El documento indica tres integrantes. |

## Decisiones internas acordadas

El usuario eligió MARS y cobertura del lenguaje actual completo durante la
planificación. La distribución conserva Daniel → Nadissa → Dulce → Nelson.

| Tema | Decisión de diseño |
|---|---|
| Simulador | MARS 4.5; una configuración reproducible en GUI y terminal. |
| Alcance | Todas las capacidades actuales, no solo el mínimo enumerado. |
| Entrada backend | IR estructurada, tipos y layouts; nunca parsear el texto TAC. |
| Compatibilidad | APIs y pruebas previas conservadas; wrapper nuevo para MIPS. |
| Memoria | Direcciones de 32 bits; padding explícito para regiones abstractas de ocho bytes. |
| Registros | Asignación local conservadora, respaldos en memoria y flush en fronteras. |
| Runtime | Heap sin GC, comprobaciones de errores y manejadores de lenguaje propios. |
| Ejecución | Acción explícita, separada de generación; sin iniciar MARS al importar módulos. |
| Entregas | Cuatro bloques secuenciales, cada uno con pruebas y documentación propias. |

Estos acuerdos no se atribuyen al profesor. Las reglas numéricas, de memoria,
impresión y excepciones se definen en [DISENO_MIPS.md](DISENO_MIPS.md).

## Confirmaciones y precondiciones pendientes

| Tema | Responsable | Condición de cierre |
|---|---|---|
| Equipo de cuatro en esta fase | Equipo | Referencia a autorización del profesor y fecha. La autorización histórica se comprueba antes de darla por extensible. |
| Base de pruebas | Daniel / propietario del cambio | Resolver el fixture local de listas y registrar suite limpia. |
| Enunciado reproducible | Equipo | Asegurar que la fuente raíz acompaña el checkout de entrega. |
| MARS disponible | Daniel | Procedencia oficial, versión, hash y prueba de ejecución. |
| Semántica externa más específica | Equipo | Si el profesor exige otra ABI o regla runtime, registrar respuesta, ajustar diseño y pruebas antes de congelar el bloque afectado. |

La comprobación de cuatro integrantes es documental y no impide preparar esta
distribución, solicitada expresamente por el usuario. Tampoco autoriza cambiar
la rúbrica ni afirmar una aprobación externa que no se ha registrado.

## Fuentes técnicas

- [Enunciado de esta entrega](../../Proyecto_Fase3_Compiladores.md).
- [Diseño TAC vigente](../proyecto2/DISENO_TAC.md).
- [Arquitectura del Proyecto 2](../proyecto2/ARQUITECTURA.md).
- [MARS 4.5 por terminal](https://dpetersanderson.github.io/Help/MarsHelpCommand.html).
- [Servicios del sistema MARS](https://dpetersanderson.github.io/Help/SyscallHelp.html).

Registrar cualquier cambio con fecha, motivo, responsable e IDs afectados.
No cambiar el alcance para marcar como aprobada una prueba que falla.

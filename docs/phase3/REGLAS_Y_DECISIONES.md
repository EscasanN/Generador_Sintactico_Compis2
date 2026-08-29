# Reglas y decisiones — Compiscript

Este documento evita que ejemplos internos contradigan el enunciado. La gramática
actual es un ejemplo base, no la versión final oficial. Cualquier diferencia con
otra gramática o corrección del profesor debe registrarse aquí con fecha. El
motor carga gramáticas en tiempo de ejecución y no se modifica por cada archivo.

## Decisiones confirmadas

| Tema | Decisión |
|---|---|
| Tamaño del equipo | Cuatro integrantes, autorizado por el profesor. |
| Entornos | Crear scopes globales, de función, clase y bloque. |
| Redeclaración | Prohibida en el mismo scope. |
| Resolución | Buscar desde el scope actual hacia sus ancestros. |
| Constantes | Deben inicializarse al declararse. |
| Argumentos | Validar cantidad y compatibilidad posicional. |
| Retorno | Validar ubicación y compatibilidad con el tipo declarado. |
| Listas | Validar homogeneidad e índices de tipo entero. |
| Clases | Validar atributos, métodos, constructores y `this`. |
| Reportes | Incluir categoría, mensaje, línea y columna. |
| Pruebas | Incluir al menos un caso exitoso y uno fallido por regla. |
| Gramática como entrada | Seleccionar otro `.g4` no requiere cambios en Python. |
| Entrada evaluada | El IDE crea, abre, edita, guarda y compila archivos `.cps`. |
| Recorrido | La integración semántica usa Listener/Visitor de ANTLR sobre el árbol nativo. |
| Árbol | Se presenta visualmente mediante nodos y aristas. |
| Aceptación | Requiere cero errores léxicos, sintácticos y semánticos. |
| Perfil JSON | Es configuración declarativa interna; no reemplaza el Listener/Visitor. |
| Modos previos | YALex y YAPar se conservan completos. |
| Generados | Se almacenan solo en `output/antlr/` y no se versionan. |
| Orden de trabajo | Daniel, Nadissa, Dulce y Nelson trabajan en ese orden. |
| Cierre de bloques | Cada responsable corrige y termina su bloque antes de integrarlo. |
| Contratos | Una API aceptada no se cambia en un bloque posterior. |
| Dependencias | Se puede usar un bloque anterior; nunca se deja trabajo para que su autor regrese. |

## Lectura literal del enunciado oficial

Salvo corrección escrita posterior del profesor, se implementan estas reglas tal
como aparecen en el PDF:

- Las condiciones de `if`, `while`, `do-while`, `for` y `switch` deben ser booleanas.
- `break` y `continue` solo son válidos dentro de bucles.
- Los operandos aritméticos deben ser `integer` o `float`.

Por tanto, `switch` no usa por defecto la semántica convencional de un
discriminante arbitrario y `break` dentro de `switch` no se permite si no existe
también un bucle envolvente. Cualquier corrección del profesor se registra antes
de cambiar el perfil y las pruebas.

## Preguntas pendientes y bloque responsable

Estas preguntas no requieren que los cuatro integrantes trabajen al mismo
tiempo. Cada una se resuelve y documenta dentro del bloque indicado, antes de
cerrarlo:

- Daniel: compatibilidad de tipos, literales y `null`;
- Nadissa: declaraciones, funciones, control, scopes y clases;
- Dulce: diferencias sintácticas detectables desde la gramática;
- Nelson: correspondencia final entre la gramática de entrega y su perfil.

Si una respuesta del profesor cambia una decisión antes de cerrar el bloque
responsable, ese bloque incorpora la corrección. Después de aceptarse una
puerta, los bloques posteriores adaptan sus propios archivos sin pedir que un
integrante anterior regrese.

| Pregunta | Riesgo si no se resuelve |
|---|---|
| ¿La gramática final incluirá literales `float`? | El enunciado exige operaciones con `float`, pero la gramática base no contiene un literal decimal. |
| ¿La concatenación `string + string` está permitida? | Los ejemplos informales suelen usarla, pero la regla aritmética menciona solamente números. |
| ¿La falta de inicialización de `const` debe ser error sintáctico o semántico? | Si la gramática exige `= expression`, el árbol nunca contendrá una constante incompleta. |
| ¿Se exige herencia o es una mejora opcional? | Puede consumir tiempo sin aportar al mínimo evaluado. |
| ¿La gramática permite `else if` directamente? | No debe incluirse como fixture válido si solo acepta `else` seguido de bloque. |
| ¿Existe sintaxis `new Tipo[tamaño]`? | No debe asumirse para arreglos si la gramática solo permite literales de lista. |
| ¿Se permite omitir el tipo de un parámetro? | El equipo debe acordar si se infiere o se representa como tipo desconocido. |
| ¿Se permite declarar una variable sin tipo y sin inicializador? | Sin ninguna de las dos fuentes no hay información suficiente para determinar su tipo. |
| ¿Una función sin anotación de retorno es `void` o infiere el tipo? | Cambia la validación de cada sentencia `return`. |
| ¿`null` puede asignarse a clases y arreglos? | Se necesita una única regla de compatibilidad para todos los integrantes. |
| ¿El cuerpo de un `if` requiere llaves obligatoriamente? | La gramática exige bloques, pero algunos ejemplos pueden mostrar sentencias individuales. |

El perfil JSON es una decisión interna de arquitectura: asocia reglas con
acciones seguras, mientras un Listener/Visitor de ANTLR realiza el recorrido
exigido. Si el profesor entrega acciones o convenciones adicionales, se traducen
al mismo registro sin ejecutar código arbitrario desde el perfil.

## Reglas para crear fixtures

- Cada fixture debe parsearse correctamente antes de usarse para probar semántica, salvo que sea una prueba sintáctica negativa.
- No se inventarán palabras clave ni construcciones ausentes de la gramática
  seleccionada y el enunciado.
- Un caso semántico negativo debe tener sintaxis válida; de lo contrario solo demuestra un error del parser.
- Cada fixture indicará qué regla valida y qué diagnósticos espera.
- Cada fixture registra la gramática y regla inicial usadas.
- Cuando se entregue otra gramática se carga desde el IDE y se ejecuta nuevamente
  la matriz; no se modifica el motor.

## Matriz inicial de cobertura

| Dominio | Casos mínimos |
|---|---|
| Tipos | aritmética, lógica, comparación, asignación y constante |
| Ámbitos | no declarado, redeclaración, bloque anidado y shadowing |
| Funciones | argumentos, retornos, recursión, anidamiento y closure |
| Control | condiciones, `break`, `continue`, `return` y código muerto |
| Clases | atributo, método, constructor y `this` |
| Listas | homogeneidad, índice y asignación de elemento |
| Integración | programa válido completo y programa con errores de varias categorías |

Esta tabla es solo un resumen. La fuente de verdad para casos positivos,
negativos, responsables y evidencia es
[`MATRIZ_CUMPLIMIENTO.md`](MATRIZ_CUMPLIMIENTO.md).

## Alcance no mínimo

`foreach`, `try/catch`, herencia y `new` aparecen en la especificación de
ejemplo, pero no están enumerados como reglas semánticas mínimas en el PDF. Se
implementan después de completar la matriz oficial, salvo que la gramática final
o una instrucción del profesor los vuelva obligatorios.

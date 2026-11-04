# Proyecto Fase 3: Generación de Código

**Construcción de Compiladores** — Octubre, 2026

---

## Descripción

Esta actividad corresponde a la fase final en la construcción de un compilador para **Compiscript**, un lenguaje basado en un subconjunto de TypeScript: la generación de código de máquina o lenguaje ensamblador. A partir del análisis semántico y del código intermedio (TAC), se debe traducir esta representación intermedia a un código de bajo nivel. Para ello se utilizará **MIPS**, un lenguaje ensamblador utilizado convencionalmente de forma educativa para aterrizar los conceptos de compilación.

- **Secuencias de Llamada y Retorno:** Traducción de las llamadas y retornos de procedimientos, preservando el estado de la memoria mediante el manejo del stack pointer.
- **Asignación de Registros:** Algoritmo `getReg()` para asignar registros de MIPS, o uso de la pila, durante la traducción del código intermedio.
- **Generación de Código MIPS:** Código ensamblador ejecutable en un simulador de MIPS.

**Modalidad:** Grupos de 3 integrantes.

## Objetivos

### Generales

- Implementar un generador de código MIPS funcional a partir del código intermedio de Compiscript.
- Aplicar los conceptos de secuencias de llamada, registros de activación y asignación de registros sobre una arquitectura real.
- Validar el código generado mediante su ejecución en un simulador de MIPS.

### Específicos

- Implementar un algoritmo de generación de secuencias de llamada y de retorno de procedimientos.
- Implementar un algoritmo de asignación de registros (`getReg()`) o de uso de pila.
- Traducir el código de tres direcciones a código ensamblador MIPS.
- Ejecutar el código generado en un simulador de MIPS y validar su correcto funcionamiento.
- Implementar una batería de pruebas que valide casos exitosos y fallidos de la generación de código.
- Desarrollar un IDE que permita escribir y compilar código Compiscript.

## Especificaciones

El generador de código debe cumplir, como mínimo, con lo siguiente:

### Secuencias de Llamada y Retorno

- Traducción del código de tres direcciones a código MIPS capaz de realizar saltos hacia y desde procedimientos (funciones).
- Preservación del estado general de la memoria al invocar y retornar de un procedimiento, mediante el manejo del stack pointer (`$sp`).
- Paso de parámetros, almacenamiento de la dirección de retorno y del valor de retorno, conforme al diseño de registros de activación.

### Asignación de Registros

- Implementación de la función `getReg()` para asignar registros libres durante la traducción del código intermedio.
- Uso apropiado de los distintos tipos de registros de MIPS, tales como los temporales (`$t`) y los guardados (`$s`).
- Opción de utilizar la pila para almacenar los valores de las operaciones cuando no existan registros disponibles.

### Generación de Código MIPS

- Generación de código ensamblador MIPS a partir del código intermedio.
- Ejecución del código generado por medio de un simulador de MIPS, validando que se ejecute correctamente.

### Entrada

- Archivo fuente de Compiscript con extensión `.cps`.

### Salida

- Código ensamblador MIPS generado a partir del programa fuente.
- Reporte de errores encontrados durante la compilación.

## Funcionamiento del Programa

1. El usuario carga o escribe un archivo `.cps` a través del IDE.
2. El analizador léxico y sintáctico (ANTLR) construye el árbol sintáctico.
3. El analizador semántico recorre el árbol validando las reglas del lenguaje y construyendo la tabla de símbolos.
4. Se genera el código intermedio (TAC) a partir del árbol sintáctico.
5. El generador de código traduce el código intermedio a MIPS, aplicando las secuencias de llamada y retorno y la asignación de registros.
6. El código MIPS generado se ejecuta en un simulador de MIPS para validar su funcionamiento.
7. El usuario puede ejecutar la batería de pruebas para validar casos exitosos y fallidos.

## Entregables

- Un repositorio de GitHub, con commits individuales que evidencien claramente la contribución de cada integrante (no se permite compartir commits en conjunto).
- Batería de pruebas que valide casos exitosos y fallidos de la generación de código, presente y funcional al momento de la evaluación.
- Documentación de la arquitectura de la implementación y documentación de cómo ejecutar el compilador.
- IDE funcional que permita escribir y compilar código Compiscript.

## Evaluación

### Requisitos para Calificación

> Para poder optar a calificación, **el programa debe funcionar correctamente el día de la presentación**. El proyecto debe estar correctamente documentado y organizado.

| Componente | Descripción | Puntos |
|---|---|---|
| Llamadas y Retornos | Algoritmo de generación de secuencias de llamada y retorno de procedimientos | 20 pts |
| Asignación de Registros | Algoritmo de asignación de registros (`getReg()`) o uso de pila | 20 pts |
| Código MIPS | Generación de código MIPS funcional y ejecutado en un simulador de MIPS, con batería de pruebas | 60 pts |
| **Total** | | **100 pts** |

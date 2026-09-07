# Instrucciones de ejecución

## 1. Requisitos

Instalar antes de ejecutar el proyecto:

- Python 3.10 o superior.
- Java 11 o superior, disponible en `PATH`.
- Graphviz, disponible en `PATH`.
- Git, si se trabaja desde el repositorio.

Comprobar Java y Graphviz desde PowerShell:

```powershell
java -version
dot -V
python --version
```

## 2. Abrir el proyecto

Desde PowerShell, ubicarse en la carpeta raíz:

```powershell
Set-Location "C:\ruta\al\Generador_Sintactico_Compis2"
```

La carpeta raíz debe contener `README.md`, `requirements.txt` y `src/`.

## 3. Crear el entorno virtual

Crear un entorno virtual una sola vez:

```powershell
python -m venv .venv
```

Activarlo en PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación, ejecutar una vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Después de activar el entorno, instalar las dependencias:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Para salir del entorno virtual:

```powershell
deactivate
```

## 4. Ejecutar la interfaz gráfica

Con el entorno virtual activado:

```powershell
python -m src.main
```

También funciona:

```powershell
python src/main.py
```

La aplicación permite utilizar dos modos:

- **YALex + YAPar:** analiza archivos `.yal`, `.yapar` y entradas de texto.
- **ANTLR (.g4):** carga una gramática ANTLR, selecciona una regla inicial y
  analiza la entrada correspondiente.

## 5. Ejecutar el modo YALex + YAPar desde consola

Para ejecutar el analizador completo desde la terminal:

```powershell
python src/main.py --cli `
  <archivo.yal> <archivo.yapar> <entrada.txt>
```

Ejemplo:

```powershell
python src/main.py --cli `
  tests/cases/01_arithmetic_id/arithmetic.yal `
  tests/cases/01_arithmetic_id/arithmetic.yapar `
  tests/cases/01_arithmetic_id/input.txt
```

El comando muestra:

- cantidad de estados LR(0);
- conflictos SLR(1) y LALR;
- disponibilidad de LL(1);
- resultado `ACCEPT` o `REJECT` para cada entrada;
- imagen del automata LR(0) en `output/`.

Los nombres de los archivos de ejemplo pueden variar. Si no existe alguno,
utilizar los archivos `.yal`, `.yapar` y `.txt` disponibles en `tests/`.

## 6. Ejecutar solamente el pipeline léxico YALex

```powershell
python src/main.py --lex <archivo.yal>
```

Este comando construye:

1. especificacion lexica;
2. NFA mediante Thompson;
3. DFA mediante construccion de subconjuntos;
4. DFA minimo mediante Hopcroft;
5. imagenes de los automatas;
6. lexer Java en `output/Lexer.java`.

Ejemplo:

```powershell
python src/main.py --lex tests/cases/01_arithmetic_id/arithmetic.yal
```

## 7. Ejecutar Compiscript con ANTLR desde la GUI

1. Ejecutar `python -m src.main`.
2. Seleccionar **ANTLR (.g4)** o presionar **Open G4**.
3. Abrir:

   ```text
   src/compiscript/grammar/Compiscript.g4
   ```

4. Seleccionar la regla inicial `program`.
5. Cargar el perfil:

   ```text
   semantic_profiles/compiscript.semantic.json
   ```

6. Crear un archivo `.cps` con **File -> New .cps** o abrir uno existente.
7. Presionar **Analyze** o usar `Ctrl+R`.

El IDE muestra tokens, arbol sintactico, diagnosticos, tabla de simbolos y
resultado semantico. `ACCEPT` solo aparece cuando no existen errores lexicos,
sintacticos ni semanticos.

## 8. Ejecucion de ANTLR sin GUI

Para usar el frontend semantico generico desde Python:

```python
from src.semantic.antlr_adapter import analyze_semantics_with_g4

result = analyze_semantics_with_g4(
    grammar_path="tests/antlr_mode/fixtures/MiniCalc.g4",
    source="10 + 20 - 5",
    profile_path="semantic_profiles/minicalc.semantic.json",
    start_rule="root",
    source_path="ejemplo.mc",
)

print("ACCEPT" if result.accepted else "REJECT")
```

Para Compiscript, el punto de entrada completo usa las acciones extendidas del
perfil:

```python
from src.gui.semantic_bridge import analyze_semantics_with_extensions

result = analyze_semantics_with_extensions(
    grammar_path="src/compiscript/grammar/Compiscript.g4",
    source=open("programa.cps", encoding="utf-8").read(),
    profile_path="semantic_profiles/compiscript.semantic.json",
    start_rule="program",
    source_path="programa.cps",
)

print(result.accepted)
```

## 9. ANTLR y la caché

En el primer análisis ANTLR, el proyecto puede descargar automáticamente
`antlr-4.13.2-complete.jar` y guardarlo en:

```text
output/antlr/tools/
```

Los parsers generados se guardan en:

```text
output/antlr/generated/
```

La generación se reutiliza mientras no cambie la versión de ANTLR ni el
contenido de la gramática.

Para utilizar un JAR local sin descargarlo:

```powershell
$env:ANTLR4_JAR = "C:\ruta\antlr-4.13.2-complete.jar"
python -m src.main
```

El generador requiere que Java y el runtime de Python utilicen ANTLR 4.13.2.

## 10. Ejecutar las pruebas

Ejecutar las pruebas del frontend ANTLR:

```powershell
python -m pytest tests/antlr_mode -q
```

Ejecutar las pruebas semanticas:

```powershell
python -m pytest tests/semantic -q
```

Ejecutar las pruebas de la GUI:

```powershell
python -m pytest tests/gui -q
```

Ejecutar toda la suite:

```powershell
python -m pytest -q
```

Comprobar solamente la sintaxis de los archivos Python:

```powershell
python -m compileall -q src tests
```

## 11. Solucion de problemas comunes

### `No module named pytest`

Activar `.venv` e instalar las dependencias:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### `Java no esta instalado` o ANTLR no genera el parser

Comprobar:

```powershell
java -version
Get-Command java
```

Java debe estar instalado y disponible en el `PATH`.

### Graphviz no esta disponible

Comprobar:

```powershell
dot -V
Get-Command dot
```

Instalar Graphviz y agregar su carpeta `bin` al `PATH`.

### La descarga de ANTLR falla

Descargar manualmente `antlr-4.13.2-complete.jar`, guardar la ruta en
`ANTLR4_JAR` y ejecutar nuevamente:

```powershell
$env:ANTLR4_JAR = "C:\ruta\antlr-4.13.2-complete.jar"
```

### La regla inicial no existe

Usar la primera regla de parser detectada por el IDE o seleccionar una regla
que realmente exista en la gramática `.g4`.

### Se obtiene `REJECT`

Revisar los diagnósticos indicando si el problema pertenece a:

- Lexer: token no reconocido;
- Parser: estructura inválida o entrada sobrante;
- Semántica: tipos, scopes, funciones, clases o reglas de control.

## 12. Limpieza de archivos generados

Los archivos generados se guardan en `output/`. Para limpiar la caché desde
PowerShell:

```powershell
Remove-Item -Recurse -Force output\antlr\generated
Remove-Item -Recurse -Force output\antlr\tools
```

Solo ejecutar esta limpieza si se desea forzar una nueva generación o descarga.
No eliminar archivos fuente de `src/` ni los casos de prueba.

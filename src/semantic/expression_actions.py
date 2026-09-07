"""Acciones independientes del analizador para tipar y validar expresiones."""

from __future__ import annotations

import re
from collections.abc import Iterable

from src.semantic.diagnostics import (
    DiagnosticBag,
    DiagnosticCategory,
    SourceLocation,
)
from src.semantic.types import (
    BOOLEAN,
    ERROR,
    FLOAT,
    INTEGER,
    NULL,
    STRING,
    UNKNOWN,
    ArrayType,
    _compatibility_is_unknown,
    _contains_error,
    common_type,
    is_assignable,
    is_boolean,
    is_numeric,
)
from src.semantic.values import SemanticValue

_INTEGER_LITERAL = re.compile(r"[0-9]+\Z")
_FLOAT_LITERAL = re.compile(
    r"(?:(?:[0-9]+\.[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|"
    r"[0-9]+[eE][+-]?[0-9]+)\Z"
)


class ExpressionActions:
    """Valida expresiones mientras acumula diagnósticos recuperables.

    Argumentos:
        diagnostics: Acumulador de destino para cada problema semántico.

    Retorna:
        Un servicio de acciones asociado con el acumulador recibido.

    Lanza:
        TypeError: Si se omite el acumulador de diagnósticos obligatorio.
    """

    def __init__(self, diagnostics: DiagnosticBag) -> None:
        """Asocia todas las acciones con un acumulador de diagnósticos compartido.

        Argumentos:
            diagnostics: Acumulador de destino para problemas semánticos.

        Retorna:
            ``None``.

        Lanza:
            TypeError: Si se omite ``diagnostics``.
        """
        self._diagnostics = diagnostics

    def literal(
        self,
        kind: str,
        text: str,
        location: SourceLocation,
    ) -> SemanticValue:
        """Interpreta un literal compatible como un valor semántico tipado.

        Los tipos admitidos son ``integer``, ``float``, ``string``, ``boolean``
        y ``null``. Los signos se mantienen como operadores unarios y no como
        parte del texto del literal numérico.

        Argumentos:
            kind: Tipo estable de literal proporcionado por el llamador.
            text: Escritura original del literal.
            location: Ubicación del literal basada en uno.

        Retorna:
            Una constante no asignable o un valor de tipo ``ERROR`` si el tipo
            de literal o su escritura no son válidos.

        Lanza:
            No lanza excepciones durante el análisis semántico normal; la
            entrada inválida se informa mediante el acumulador de diagnósticos.
        """
        normalized_kind = kind.strip().lower()
        try:
            if normalized_kind == "integer" and _INTEGER_LITERAL.fullmatch(text):
                return SemanticValue(INTEGER, int(text), location=location)
            if normalized_kind == "float" and _FLOAT_LITERAL.fullmatch(text):
                return SemanticValue(FLOAT, float(text), location=location)
            if normalized_kind == "string":
                return SemanticValue(
                    STRING,
                    _parse_string_literal(text),
                    location=location,
                )
            if normalized_kind == "boolean" and text in {"true", "false"}:
                return SemanticValue(BOOLEAN, text == "true", location=location)
            if normalized_kind == "null" and text == "null":
                return SemanticValue(NULL, None, location=location)
        except ValueError:
            pass

        self._diagnostics.add(
            DiagnosticCategory.TYPE,
            f"Invalid {normalized_kind or 'unknown'} literal: {text!r}",
            location,
        )
        return SemanticValue(ERROR, location=location)

    def unary(
        self,
        operator: str,
        operand: SemanticValue,
        location: SourceLocation,
    ) -> SemanticValue:
        """Valida un signo numérico o una negación booleana.

        Argumentos:
            operator: ``+``, ``-`` o ``!``.
            operand: Valor que se validará.
            location: Ubicación basada en uno de la expresión completa.

        Retorna:
            Un resultado que conserva el tipo numérico para operadores de signo
            o ``boolean`` para la negación. Los tipos ``ERROR`` y ``UNKNOWN``
            existentes se propagan sin diagnósticos adicionales.

        Lanza:
            No lanza excepciones durante el análisis semántico normal; las
            operaciones inválidas se informan mediante los diagnósticos.
        """
        if operator not in {"+", "-", "!"}:
            self._diagnostics.add(
                DiagnosticCategory.GENERAL,
                f"Unsupported unary operator: {operator!r}",
                location,
            )
            return SemanticValue(ERROR, location=location)
        if _contains_error(operand.type):
            return SemanticValue(ERROR, location=location)
        if operand.type == UNKNOWN:
            return SemanticValue(UNKNOWN, location=location)
        if operator in {"+", "-"} and is_numeric(operand.type):
            return SemanticValue(operand.type, location=location)
        if operator == "!" and is_boolean(operand.type):
            return SemanticValue(BOOLEAN, location=location)

        requirement = "numeric" if operator in {"+", "-"} else "boolean"
        self._diagnostics.add(
            DiagnosticCategory.TYPE,
            f"Operator {operator!r} requires a {requirement} operand; got {operand.type}",
            location,
        )
        return SemanticValue(ERROR, location=location)

    def binary(
        self,
        operator: str,
        left: SemanticValue,
        right: SemanticValue,
        location: SourceLocation,
    ) -> SemanticValue:
        """Valida una expresión binaria aritmética, lógica o de comparación.

        Los operadores aritméticos son ``+``, ``-``, ``*``, ``/`` y ``%``.
        Aceptan operandos enteros o flotantes y utilizan su tipo numérico común.
        El operador ``+`` también concatena dos cadenas. Por lo tanto, la
        división de enteros conserva el tipo entero; la semántica de ejecución
        de la división queda fuera de este núcleo estático. ``&&`` y ``||``
        requieren dos operandos booleanos. Las comparaciones requieren
        compatibilidad de asignación en al menos una dirección y retornan
        ``boolean``.

        Argumentos:
            operator: Escritura del operador binario.
            left: Valor del operando izquierdo.
            right: Valor del operando derecho.
            location: Ubicación basada en uno de la expresión completa.

        Retorna:
            Un resultado tipado no asignable. ``ERROR`` se propaga sin agregar
            diagnósticos y ``UNKNOWN`` lo hace de forma conservadora sin
            inventar un error.

        Lanza:
            No lanza excepciones durante el análisis semántico normal; las
            operaciones inválidas se informan mediante los diagnósticos.
        """
        arithmetic_operators = {"+", "-", "*", "/", "%"}
        logical_operators = {"&&", "||"}
        comparison_operators = {"==", "!=", "<", "<=", ">", ">="}
        if operator not in (
            arithmetic_operators | logical_operators | comparison_operators
        ):
            self._diagnostics.add(
                DiagnosticCategory.GENERAL,
                f"Unsupported binary operator: {operator!r}",
                location,
            )
            return SemanticValue(ERROR, location=location)
        if _contains_error(left.type) or _contains_error(right.type):
            return SemanticValue(ERROR, location=location)
        if left.type == UNKNOWN or right.type == UNKNOWN:
            return SemanticValue(UNKNOWN, location=location)
        if operator == "+" and left.type == STRING and right.type == STRING:
            return SemanticValue(STRING, location=location)
        if (
            operator in arithmetic_operators
            and is_numeric(left.type)
            and is_numeric(right.type)
        ):
            return SemanticValue(
                common_type((left.type, right.type)),
                location=location,
            )

        if (
            operator in logical_operators
            and is_boolean(left.type)
            and is_boolean(right.type)
        ):
            return SemanticValue(BOOLEAN, location=location)

        if operator in comparison_operators:
            if _compatibility_is_unknown(left.type, right.type):
                return SemanticValue(UNKNOWN, location=location)
            compatible = is_assignable(left.type, right.type) or is_assignable(
                right.type, left.type
            )
            if compatible:
                return SemanticValue(BOOLEAN, location=location)
            self._diagnostics.add(
                DiagnosticCategory.TYPE,
                (
                    f"Operator {operator!r} requires compatible operands; got "
                    f"{left.type} and {right.type}"
                ),
                location,
            )
            return SemanticValue(ERROR, location=location)

        requirement = "numeric" if operator in arithmetic_operators else "boolean"
        self._diagnostics.add(
            DiagnosticCategory.TYPE,
            (
                f"Operator {operator!r} requires {requirement} operands; got "
                f"{left.type} and {right.type}"
            ),
            location,
        )
        return SemanticValue(ERROR, location=location)

    def assignment(
        self,
        target: SemanticValue,
        value: SemanticValue,
        location: SourceLocation,
    ) -> SemanticValue:
        """Valida el destino de una asignación y la compatibilidad de tipos.

        Argumentos:
            target: Valor de destino, normalmente producido al resolver un
                nombre o índice en una capa semántica posterior.
            value: Valor de la expresión fuente.
            location: Ubicación basada en uno de la asignación completa.

        Retorna:
            Un resultado no asignable con el tipo declarado del destino cuando
            es válido. Los tipos ``ERROR`` existentes y los ``UNKNOWN`` no
            resueltos se propagan sin diagnósticos de tipo adicionales.

        Lanza:
            No lanza excepciones durante el análisis semántico normal; los
            destinos o tipos inválidos se informan mediante los diagnósticos.
        """
        if _contains_error(target.type) or _contains_error(value.type):
            return SemanticValue(ERROR, location=location)
        if not target.assignable:
            self._diagnostics.add(
                DiagnosticCategory.TYPE,
                "Assignment target is not assignable",
                location,
            )
            return SemanticValue(ERROR, location=location)
        if not target.mutable:
            self._diagnostics.add(
                DiagnosticCategory.TYPE,
                "Assignment target is immutable",
                location,
            )
            return SemanticValue(ERROR, location=location)
        if target.type == UNKNOWN or value.type == UNKNOWN:
            return SemanticValue(UNKNOWN, location=location)
        if _compatibility_is_unknown(value.type, target.type):
            return SemanticValue(UNKNOWN, location=location)
        if is_assignable(value.type, target.type):
            return SemanticValue(target.type, location=location)

        self._diagnostics.add(
            DiagnosticCategory.TYPE,
            f"Cannot assign {value.type} to {target.type}",
            location,
        )
        return SemanticValue(ERROR, location=location)

    def ternary(
        self,
        condition: SemanticValue,
        true_value: SemanticValue,
        false_value: SemanticValue,
        location: SourceLocation,
    ) -> SemanticValue:
        """Valida una condición booleana y combina las ramas del ternario.

        Argumentos:
            condition: Expresión situada antes del signo de interrogación.
            true_value: Valor seleccionado si la condición es verdadera.
            false_value: Valor seleccionado si la condición es falsa.
            location: Ubicación basada en uno de la expresión ternaria completa.

        Retorna:
            El tipo común de las ramas, ``UNKNOWN`` si algún tipo relevante no
            está resuelto o ``ERROR`` ante una entrada inválida conocida. Se
            acumulan de manera independiente los errores de condición y ramas.

        Lanza:
            No lanza excepciones durante el análisis semántico normal; las
            condiciones o pares de ramas inválidos se informan mediante los
            diagnósticos.
        """
        has_error = False
        unresolved = False

        if _contains_error(condition.type):
            has_error = True
        elif condition.type == UNKNOWN:
            unresolved = True
        elif not is_boolean(condition.type):
            self._diagnostics.add(
                DiagnosticCategory.TYPE,
                f"Ternary condition must be boolean; got {condition.type}",
                location,
            )
            has_error = True

        branch_type = common_type((true_value.type, false_value.type))
        if branch_type == ERROR:
            if _contains_error(true_value.type) or _contains_error(false_value.type):
                has_error = True
            else:
                self._diagnostics.add(
                    DiagnosticCategory.TYPE,
                    (
                        "Ternary branches require a common type; got "
                        f"{true_value.type} and {false_value.type}"
                    ),
                    location,
                )
                has_error = True
        elif branch_type == UNKNOWN:
            unresolved = True

        if has_error:
            return SemanticValue(ERROR, location=location)
        if unresolved:
            return SemanticValue(UNKNOWN, location=location)
        return SemanticValue(branch_type, location=location)

    def array_literal(
        self,
        elements: Iterable[SemanticValue],
        location: SourceLocation,
    ) -> SemanticValue:
        """Infiere un tipo de elemento común, homogéneo o compatible, para el arreglo.

        Argumentos:
            elements: Valores de expresión en el orden de la fuente. Se acepta
                cualquier iterable y se consume una sola vez.
            location: Ubicación basada en uno del literal de arreglo completo.

        Retorna:
            Un arreglo del tipo de elemento común. El contenido vacío o no
            resuelto produce ``UNKNOWN[]``. Un elemento ``ERROR`` previo hace
            que todo el literal sea ``ERROR`` sin duplicar el diagnóstico.

        Lanza:
            Cualquier excepción producida al consumir el iterable. Las
            incompatibilidades semánticas conocidas se acumulan en su lugar.
        """
        values = tuple(elements)
        element_type = common_type(value.type for value in values)
        if element_type == ERROR:
            if not any(_contains_error(value.type) for value in values):
                rendered_types = ", ".join(str(value.type) for value in values)
                self._diagnostics.add(
                    DiagnosticCategory.ARRAY,
                    f"Array elements require a common type; got {rendered_types}",
                    location,
                )
            return SemanticValue(ERROR, location=location)
        return SemanticValue(ArrayType(element_type), location=location)

    def index(
        self,
        container: SemanticValue,
        index: SemanticValue,
        location: SourceLocation,
    ) -> SemanticValue:
        """Valida la indexación de un arreglo y expone una dimensión del elemento.

        Argumentos:
            container: Valor que debe tener un tipo de arreglo.
            index: Valor que debe tener exactamente el tipo entero.
            location: Ubicación basada en uno de la indexación completa.

        Retorna:
            El valor del elemento del arreglo. Sus capacidades de asignación y
            mutabilidad siguen al contenedor para que capas posteriores validen
            ``array[i] =``. Los operandos ``ERROR`` y ``UNKNOWN`` existentes se
            propagan de forma segura.

        Lanza:
            No lanza excepciones durante el análisis semántico normal; los
            contenedores o índices inválidos se informan mediante diagnósticos.
        """
        container_has_error = _contains_error(container.type)
        index_has_error = _contains_error(index.type)
        has_error = container_has_error or index_has_error
        unresolved = container.type == UNKNOWN or index.type == UNKNOWN

        if (
            not container_has_error
            and container.type != UNKNOWN
            and not isinstance(container.type, ArrayType)
        ):
            self._diagnostics.add(
                DiagnosticCategory.ARRAY,
                f"Indexing requires an array; got {container.type}",
                location,
            )
            has_error = True
        if not index_has_error and index.type not in {UNKNOWN, INTEGER}:
            self._diagnostics.add(
                DiagnosticCategory.ARRAY,
                f"Array index must be integer; got {index.type}",
                location,
            )
            has_error = True

        if has_error:
            return SemanticValue(ERROR, location=location)
        if unresolved:
            return SemanticValue(UNKNOWN, location=location)
        if not isinstance(container.type, ArrayType):
            return SemanticValue(ERROR, location=location)
        return SemanticValue(
            container.type.element_type,
            assignable=container.assignable,
            mutable=container.mutable,
            symbol=container.symbol,
            location=location,
        )


def _parse_string_literal(text: str) -> str:
    """Interpreta comillas simples o dobles coincidentes y escapes comunes."""
    if len(text) < 2 or text[0] not in {'"', "'"} or text[-1] != text[0]:
        raise ValueError("string literal must have matching quotes")

    escapes = {
        "\\": "\\",
        '"': '"',
        "'": "'",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "b": "\b",
        "f": "\f",
    }
    result: list[str] = []
    index = 1
    while index < len(text) - 1:
        character = text[index]
        if character != "\\":
            result.append(character)
            index += 1
            continue
        index += 1
        if index >= len(text) - 1 or text[index] not in escapes:
            raise ValueError("unsupported or incomplete string escape")
        result.append(escapes[text[index]])
        index += 1
    return "".join(result)

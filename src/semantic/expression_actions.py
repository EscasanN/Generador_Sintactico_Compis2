"""Parser-independent actions for typing and validating expressions."""

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
    """Validate expressions while accumulating recoverable diagnostics.

    Args:
        diagnostics: Destination bag for every semantic issue.

    Returns:
        An action service bound to the supplied bag.

    Raises:
        TypeError: If the required diagnostic bag is omitted.
    """

    def __init__(self, diagnostics: DiagnosticBag) -> None:
        """Bind all actions to a shared diagnostic accumulator.

        Args:
            diagnostics: Destination bag for semantic issues.

        Returns:
            None.

        Raises:
            TypeError: If ``diagnostics`` is omitted.
        """
        self._diagnostics = diagnostics

    def literal(
        self,
        kind: str,
        text: str,
        location: SourceLocation,
    ) -> SemanticValue:
        """Parse a supported literal into a typed semantic value.

        Supported kinds are ``integer``, ``float``, ``string``, ``boolean``
        and ``null``. Signs remain unary operators rather than part of numeric
        literal text.

        Args:
            kind: Stable literal kind supplied by the caller.
            text: Original literal spelling.
            location: One-based source location for the literal.

        Returns:
            A non-assignable constant, or a value of type ``ERROR`` when the
            kind or spelling is invalid.

        Raises:
            No exceptions during normal semantic analysis; invalid input is
            reported through the diagnostic bag.
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
        """Validate numeric sign or boolean negation.

        Args:
            operator: ``+``, ``-`` or ``!``.
            operand: Value to validate.
            location: One-based location of the complete expression.

        Returns:
            A result preserving the numeric type for sign operators or
            ``boolean`` for negation. Existing ``ERROR`` and ``UNKNOWN`` types
            propagate without extra diagnostics.

        Raises:
            No exceptions during normal semantic analysis; invalid operations
            are reported through the diagnostic bag.
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
        """Validate a binary arithmetic, logical, or comparison expression.

        The confirmed arithmetic operators are ``+``, ``-``, ``*`` and ``/``.
        They accept only integer or float operands, and use their common
        numeric type. Consequently integer division remains typed as integer;
        runtime division semantics are outside this static core. ``&&`` and
        ``||`` require two boolean operands. Comparisons require assignment
        compatibility in at least one direction and return ``boolean``.

        Args:
            operator: Binary operator spelling.
            left: Left operand value.
            right: Right operand value.
            location: One-based location of the complete expression.

        Returns:
            A non-assignable typed result. ``ERROR`` propagates silently, and
            ``UNKNOWN`` propagates conservatively without inventing an error.

        Raises:
            No exceptions during normal semantic analysis; invalid operations
            are reported through the diagnostic bag.
        """
        arithmetic_operators = {"+", "-", "*", "/"}
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
        """Validate assignment target capabilities and type compatibility.

        Args:
            target: Destination value, normally produced by name or index
                resolution in a later semantic layer.
            value: Source expression value.
            location: One-based location of the complete assignment.

        Returns:
            A non-assignable result with the target's declared type when valid.
            Existing ``ERROR`` and unresolved ``UNKNOWN`` types propagate
            without extra type diagnostics.

        Raises:
            No exceptions during normal semantic analysis; invalid targets or
            types are reported through the diagnostic bag.
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
        """Validate a boolean condition and join both ternary branches.

        Args:
            condition: Expression before the question mark.
            true_value: Value selected by a true condition.
            false_value: Value selected by a false condition.
            location: One-based location of the complete ternary expression.

        Returns:
            The common branch type, ``UNKNOWN`` when any relevant type is
            unresolved, or ``ERROR`` after known invalid input. Independent
            condition and branch errors are both accumulated.

        Raises:
            No exceptions during normal semantic analysis; invalid conditions
            or branch pairs are reported through the diagnostic bag.
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
        """Infer a homogeneous or otherwise valid common array element type.

        Args:
            elements: Expression values in source order. Any iterable is
                accepted and consumed once.
            location: One-based location of the complete array literal.

        Returns:
            An array of the common element type. Empty or unresolved contents
            produce ``UNKNOWN[]``. A prior element ``ERROR`` makes the whole
            literal ``ERROR`` without adding a duplicate diagnostic.

        Raises:
            Any exception raised while consuming the supplied iterable.
            Known semantic incompatibilities are accumulated instead.
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
        """Validate array indexing and expose one element dimension.

        Args:
            container: Value expected to have an array type.
            index: Value required to have exactly the integer type.
            location: One-based location of the complete index expression.

        Returns:
            The array element value. Its assignment and mutability capabilities
            follow the container so later layers can validate ``array[i] =``.
            Existing ``ERROR`` and ``UNKNOWN`` operands propagate safely.

        Raises:
            No exceptions during normal semantic analysis; invalid containers
            or indices are reported through the diagnostic bag.
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
    """Parse matching single or double quotes and common escapes."""
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

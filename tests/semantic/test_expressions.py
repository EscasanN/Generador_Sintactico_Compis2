"""Tests for framework-neutral semantic values and expression actions."""

from dataclasses import FrozenInstanceError, dataclass

import pytest

from src.semantic.diagnostics import DiagnosticBag, DiagnosticCategory, SourceLocation
from src.semantic.expression_actions import ExpressionActions
from src.semantic.types import (
    BOOLEAN,
    ERROR,
    FLOAT,
    INTEGER,
    NULL,
    STRING,
    UNKNOWN,
    ArrayType,
    ClassType,
    FunctionType,
    ErrorType,
    UnknownType,
)
from src.semantic.values import SemanticValue


@dataclass(frozen=True)
class ExampleSymbol:
    """Minimal structural symbol used to verify the neutral protocol."""

    name: str


def value(type_, *, assignable: bool = False, mutable: bool = False) -> SemanticValue:
    """Build a semantic value at a stable test location."""
    return SemanticValue(
        type=type_,
        assignable=assignable,
        mutable=mutable,
        location=SourceLocation(1, 1),
    )


def test_semantic_value_is_immutable_and_keeps_only_neutral_data() -> None:
    """Losing symbol or source metadata would break the next block's API."""
    symbol = ExampleSymbol("counter")
    location = SourceLocation(4, 7, source_path="values.cps")
    semantic_value = SemanticValue(
        type=INTEGER,
        constant_value=42,
        assignable=True,
        mutable=True,
        symbol=symbol,
        location=location,
    )

    assert semantic_value == SemanticValue(INTEGER, 42, True, True, symbol, location)
    assert semantic_value.symbol is symbol
    assert semantic_value.location is location
    with pytest.raises(FrozenInstanceError):
        semantic_value.mutable = False  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kind", "text", "expected_type", "expected_constant"),
    [
        pytest.param("integer", "123", INTEGER, 123, id="integer"),
        pytest.param("float", "12.5", FLOAT, 12.5, id="float"),
        pytest.param("string", r'"line\nnext"', STRING, "line\nnext", id="string"),
        pytest.param("boolean", "true", BOOLEAN, True, id="true"),
        pytest.param("boolean", "false", BOOLEAN, False, id="false"),
        pytest.param("null", "null", NULL, None, id="null"),
    ],
)
def test_literal_builds_valid_typed_constants(
    kind: str,
    text: str,
    expected_type: object,
    expected_constant: object,
) -> None:
    """A wrong literal parser must fail on its independently known value."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(1, 1, source_path="literal.cps")

    result = actions.literal(kind, text, location)

    assert result.type is expected_type
    assert result.constant_value == expected_constant
    assert result.assignable is False
    assert result.mutable is False
    assert result.location is location
    assert len(diagnostics) == 0


def test_invalid_literals_accumulate_diagnostics_and_return_error_values() -> None:
    """A malformed token must not raise, print, or stop later literal checks."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(1, 1)

    results = (
        actions.literal("integer", "12x", location),
        actions.literal("float", "1", location),
        actions.literal("boolean", "TRUE", location),
        actions.literal("string", '"unterminated', location),
        actions.literal("date", "today", location),
    )

    assert all(result.type is ERROR for result in results)
    assert len(diagnostics) == 5
    assert all(item.category is DiagnosticCategory.TYPE for item in diagnostics)
    assert diagnostics.has_errors is True


@pytest.mark.parametrize(
    ("operator", "left_type", "right_type", "expected_type"),
    [
        pytest.param("+", INTEGER, INTEGER, INTEGER, id="TYP-01-success-add"),
        pytest.param("-", FLOAT, INTEGER, FLOAT, id="TYP-01-success-subtract-promotes"),
        pytest.param("*", INTEGER, FLOAT, FLOAT, id="TYP-01-success-multiply-promotes"),
        pytest.param("/", INTEGER, INTEGER, INTEGER, id="TYP-01-success-divide"),
    ],
)
def test_typ_01_success_arithmetic_accepts_only_numeric_operands(
    operator: str,
    left_type: object,
    right_type: object,
    expected_type: object,
) -> None:
    """Removing numeric promotion or one arithmetic operator must fail."""
    diagnostics = DiagnosticBag()
    result = ExpressionActions(diagnostics).binary(
        operator,
        value(left_type),  # type: ignore[arg-type]
        value(right_type),  # type: ignore[arg-type]
        SourceLocation(2, 3),
    )

    assert result.type is expected_type
    assert len(diagnostics) == 0


@pytest.mark.parametrize(
    "invalid_type",
    [
        pytest.param(STRING, id="TYP-01-failure-string"),
        pytest.param(BOOLEAN, id="TYP-01-failure-boolean"),
    ],
)
def test_typ_01_failure_arithmetic_rejects_non_numeric_primitives(invalid_type: object) -> None:
    """Allowing a known nonnumeric primitive in arithmetic must fail."""
    diagnostics = DiagnosticBag()
    result = ExpressionActions(diagnostics).binary(
        "+",
        value(invalid_type),  # type: ignore[arg-type]
        value(INTEGER),
        SourceLocation(2, 3),
    )

    assert result.type is ERROR
    assert len(diagnostics) == 1
    assert diagnostics.items[0].category is DiagnosticCategory.TYPE


def test_gen_02_success_numeric_multiplication_has_semantic_meaning() -> None:
    """GEN-02 success: compatible values must retain a useful result type."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).binary(
        "*", value(INTEGER), value(FLOAT), SourceLocation(3, 1)
    )

    assert result.type is FLOAT
    assert len(diagnostics) == 0


@pytest.mark.parametrize(
    "invalid_type",
    [
        pytest.param(FunctionType((INTEGER,), INTEGER), id="GEN-02-failure-function"),
        pytest.param(ClassType("Counter"), id="GEN-02-failure-class"),
        pytest.param(ArrayType(INTEGER), id="GEN-02-failure-array"),
    ],
)
def test_gen_02_failure_numeric_operations_reject_semantically_meaningless_values(
    invalid_type: object,
) -> None:
    """GEN-02 failure: multiplying a function, class, or array must fail."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).binary(
        "*",
        value(invalid_type),  # type: ignore[arg-type]
        value(INTEGER),
        SourceLocation(3, 1),
    )

    assert result.type is ERROR
    assert len(diagnostics) == 1


def test_error_and_unknown_operands_propagate_without_duplicate_diagnostics() -> None:
    """An earlier error must stay singular, while unresolved types remain unresolved."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)

    prior_error = actions.binary("+", value(STRING), value(INTEGER), SourceLocation(1, 1))
    cascaded = actions.binary("*", prior_error, value(BOOLEAN), SourceLocation(1, 5))
    unresolved = actions.binary("+", value(UNKNOWN), value(INTEGER), SourceLocation(2, 1))

    assert prior_error.type is ERROR
    assert cascaded.type is ERROR
    assert unresolved.type is UNKNOWN
    assert len(diagnostics) == 1


def test_structurally_equal_recovery_types_propagate_like_singletons() -> None:
    """Public recovery type instances must not create identity-dependent errors."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(2, 1)

    error_result = actions.binary(
        "+", value(ErrorType()), value(INTEGER), location
    )
    unknown_result = actions.binary(
        "+", value(UnknownType()), value(INTEGER), location
    )

    assert error_result.type is ERROR
    assert unknown_result.type is UNKNOWN
    assert len(diagnostics) == 0


def test_compound_error_propagates_through_assignment_comparison_and_ternary() -> None:
    """A nested prior error must never become a valid assignment or comparison."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(2, 1)
    compound_error = value(ArrayType(ERROR))
    target = value(ArrayType(INTEGER), assignable=True, mutable=True)

    assigned = actions.assignment(target, compound_error, location)
    compared = actions.binary("==", compound_error, target, location)
    signed = actions.unary("-", compound_error, location)
    added = actions.binary("+", compound_error, value(INTEGER), location)
    selected = actions.ternary(
        value(BOOLEAN), compound_error, compound_error, location
    )

    assert assigned.type is ERROR
    assert compared.type is ERROR
    assert signed.type is ERROR
    assert added.type is ERROR
    assert selected.type is ERROR
    assert len(diagnostics) == 0


def test_compound_unknown_propagates_only_when_compatibility_depends_on_it() -> None:
    """Unknown elements defer matching arrays but cannot hide an outer mismatch."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(2, 1)
    unknown_array = value(ArrayType(UNKNOWN))
    array_target = value(ArrayType(INTEGER), assignable=True, mutable=True)
    integer_target = value(INTEGER, assignable=True, mutable=True)

    deferred_assignment = actions.assignment(array_target, unknown_array, location)
    deferred_comparison = actions.binary("==", unknown_array, value(ArrayType(INTEGER)), location)
    known_mismatch = actions.assignment(integer_target, unknown_array, location)

    assert deferred_assignment.type is UNKNOWN
    assert deferred_comparison.type is UNKNOWN
    assert known_mismatch.type is ERROR
    assert len(diagnostics) == 1


def test_typ_02_success_logical_operators_accept_boolean_operands() -> None:
    """TYP-02 success: ``true && !false`` and boolean OR remain boolean."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(5, 2)

    negated = actions.unary("!", value(BOOLEAN), location)
    conjunction = actions.binary("&&", value(BOOLEAN), negated, location)
    disjunction = actions.binary("||", conjunction, value(BOOLEAN), location)

    assert negated.type is BOOLEAN
    assert conjunction.type is BOOLEAN
    assert disjunction.type is BOOLEAN
    assert len(diagnostics) == 0


@pytest.mark.parametrize(
    ("operator", "left_type", "right_type"),
    [
        pytest.param("&&", INTEGER, BOOLEAN, id="TYP-02-failure-and-integer"),
        pytest.param("||", BOOLEAN, STRING, id="TYP-02-failure-or-string"),
    ],
)
def test_typ_02_failure_logical_binary_rejects_non_boolean_operands(
    operator: str,
    left_type: object,
    right_type: object,
) -> None:
    """TYP-02 failure: allowing either known nonboolean operand must fail."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).binary(
        operator,
        value(left_type),  # type: ignore[arg-type]
        value(right_type),  # type: ignore[arg-type]
        SourceLocation(5, 2),
    )

    assert result.type is ERROR
    assert len(diagnostics) == 1
    assert diagnostics.items[0].category is DiagnosticCategory.TYPE


def test_typ_02_failure_logical_not_rejects_non_boolean_operand() -> None:
    """TYP-02 failure: logical negation of an integer must report one error."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).unary(
        "!", value(INTEGER), SourceLocation(5, 2)
    )

    assert result.type is ERROR
    assert len(diagnostics) == 1


def test_numeric_unary_operators_preserve_numeric_type_and_reject_string() -> None:
    """Unary sign accepts numeric values without widening and rejects strings."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(6, 1)

    positive = actions.unary("+", value(INTEGER), location)
    negative = actions.unary("-", value(FLOAT), location)
    invalid = actions.unary("-", value(STRING), location)

    assert positive.type is INTEGER
    assert negative.type is FLOAT
    assert invalid.type is ERROR
    assert len(diagnostics) == 1


def test_unary_error_and_unknown_propagate_and_unknown_operator_is_reported() -> None:
    """Unary recovery must avoid cascades but still reject an unsupported operator."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(6, 1)

    prior_error = actions.unary("-", value(ERROR), location)
    unresolved = actions.unary("!", value(UNKNOWN), location)
    unsupported = actions.unary("~", value(INTEGER), location)

    assert prior_error.type is ERROR
    assert unresolved.type is UNKNOWN
    assert unsupported.type is ERROR
    assert len(diagnostics) == 1
    assert diagnostics.items[0].category is DiagnosticCategory.GENERAL


@pytest.mark.parametrize(
    ("operator", "left_type", "right_type"),
    [
        pytest.param("==", INTEGER, FLOAT, id="TYP-03-success-equal-numeric"),
        pytest.param("!=", STRING, STRING, id="TYP-03-success-not-equal-string"),
        pytest.param("<", INTEGER, INTEGER, id="TYP-03-success-less"),
        pytest.param("<=", FLOAT, INTEGER, id="TYP-03-success-less-equal"),
        pytest.param(">", INTEGER, FLOAT, id="TYP-03-success-greater"),
        pytest.param(">=", FLOAT, FLOAT, id="TYP-03-success-greater-equal"),
    ],
)
def test_typ_03_success_comparisons_accept_compatible_types(
    operator: str,
    left_type: object,
    right_type: object,
) -> None:
    """TYP-03 success: each comparison must return boolean for compatible types."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).binary(
        operator,
        value(left_type),  # type: ignore[arg-type]
        value(right_type),  # type: ignore[arg-type]
        SourceLocation(7, 4),
    )

    assert result.type is BOOLEAN
    assert len(diagnostics) == 0


@pytest.mark.parametrize(
    ("left_type", "right_type"),
    [
        pytest.param(STRING, INTEGER, id="TYP-03-failure-primitive-mismatch"),
        pytest.param(
            ArrayType(INTEGER),
            ArrayType(FLOAT),
            id="TYP-03-failure-invariant-arrays",
        ),
        pytest.param(NULL, ClassType("Node"), id="TYP-03-failure-null-class"),
    ],
)
def test_typ_03_failure_comparisons_reject_incompatible_types(
    left_type: object,
    right_type: object,
) -> None:
    """TYP-03 failure: a known incompatibility must report one type error."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).binary(
        "==",
        value(left_type),  # type: ignore[arg-type]
        value(right_type),  # type: ignore[arg-type]
        SourceLocation(7, 4),
    )

    assert result.type is ERROR
    assert len(diagnostics) == 1
    assert diagnostics.items[0].category is DiagnosticCategory.TYPE


def test_comparison_propagates_error_and_unknown_without_cascades() -> None:
    """A comparison cannot validate unresolved values or repeat a prior error."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(7, 4)

    previous = actions.binary("+", value(STRING), value(INTEGER), location)
    cascaded = actions.binary("==", previous, value(STRING), location)
    unresolved = actions.binary("<", value(UNKNOWN), value(INTEGER), location)

    assert cascaded.type is ERROR
    assert unresolved.type is UNKNOWN
    assert len(diagnostics) == 1


@pytest.mark.parametrize(
    ("target_type", "source_type"),
    [
        pytest.param(INTEGER, INTEGER, id="TYP-04-success-exact"),
        pytest.param(FLOAT, INTEGER, id="TYP-04-success-integer-to-float"),
    ],
)
def test_typ_04_success_assignment_accepts_compatible_mutable_targets(
    target_type: object,
    source_type: object,
) -> None:
    """TYP-04 success: valid assignment must preserve the declared target type."""
    diagnostics = DiagnosticBag()
    location = SourceLocation(8, 3)

    result = ExpressionActions(diagnostics).assignment(
        value(target_type, assignable=True, mutable=True),  # type: ignore[arg-type]
        value(source_type),  # type: ignore[arg-type]
        location,
    )

    assert result.type is target_type
    assert result.location is location
    assert result.assignable is False
    assert len(diagnostics) == 0


@pytest.mark.parametrize(
    ("target_type", "source_type"),
    [
        pytest.param(INTEGER, STRING, id="TYP-04-failure-string-to-integer"),
        pytest.param(INTEGER, FLOAT, id="TYP-04-failure-narrowing"),
    ],
)
def test_typ_04_failure_assignment_rejects_incompatible_values(
    target_type: object,
    source_type: object,
) -> None:
    """TYP-04 failure: incompatible assignment must report one type error."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).assignment(
        value(target_type, assignable=True, mutable=True),  # type: ignore[arg-type]
        value(source_type),  # type: ignore[arg-type]
        SourceLocation(8, 3),
    )

    assert result.type is ERROR
    assert len(diagnostics) == 1
    assert diagnostics.items[0].category is DiagnosticCategory.TYPE


def test_assignment_to_constant_and_nonassignable_value_reports_one_error_each() -> None:
    """A constant and a temporary are distinct invalid assignment targets."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(9, 1)

    constant_result = actions.assignment(
        value(INTEGER, assignable=True, mutable=False), value(INTEGER), location
    )
    temporary_result = actions.assignment(value(INTEGER), value(INTEGER), location)

    assert constant_result.type is ERROR
    assert temporary_result.type is ERROR
    assert len(diagnostics) == 2
    assert "immutable" in diagnostics.items[0].message.lower()
    assert "assignable" in diagnostics.items[1].message.lower()


def test_assignment_propagates_error_and_unknown_without_duplicate_diagnostics() -> None:
    """Recovery types must not create a second assignment diagnostic."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(9, 1)
    target = value(INTEGER, assignable=True, mutable=True)

    previous = actions.binary("+", value(STRING), value(INTEGER), location)
    cascaded = actions.assignment(target, previous, location)
    unresolved = actions.assignment(target, value(UNKNOWN), location)

    assert cascaded.type is ERROR
    assert unresolved.type is UNKNOWN
    assert len(diagnostics) == 1


@pytest.mark.parametrize(
    ("true_type", "false_type", "expected_type"),
    [
        pytest.param(STRING, STRING, STRING, id="ternary-exact-branches"),
        pytest.param(INTEGER, FLOAT, FLOAT, id="ternary-numeric-promotion"),
    ],
)
def test_valid_ternary_requires_boolean_condition_and_joins_branch_types(
    true_type: object,
    false_type: object,
    expected_type: object,
) -> None:
    """A valid ternary must expose the independently known common branch type."""
    diagnostics = DiagnosticBag()
    location = SourceLocation(10, 2)

    result = ExpressionActions(diagnostics).ternary(
        value(BOOLEAN),
        value(true_type),  # type: ignore[arg-type]
        value(false_type),  # type: ignore[arg-type]
        location,
    )

    assert result.type is expected_type
    assert result.location is location
    assert len(diagnostics) == 0


def test_invalid_ternary_accumulates_condition_and_branch_errors() -> None:
    """Independent condition and branch failures must both remain visible."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).ternary(
        value(INTEGER),
        value(STRING),
        value(BOOLEAN),
        SourceLocation(10, 2),
    )

    assert result.type is ERROR
    assert len(diagnostics) == 2
    assert all(item.category is DiagnosticCategory.TYPE for item in diagnostics)


def test_ternary_propagates_existing_error_and_unknown_without_cascades() -> None:
    """Recovery branches must not duplicate errors or claim a concrete type."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(10, 2)
    previous = actions.binary("+", value(STRING), value(INTEGER), location)

    cascaded = actions.ternary(value(BOOLEAN), previous, value(INTEGER), location)
    unknown_condition = actions.ternary(
        value(UNKNOWN), value(INTEGER), value(INTEGER), location
    )
    unknown_branch = actions.ternary(
        value(BOOLEAN), value(UNKNOWN), value(INTEGER), location
    )

    assert cascaded.type is ERROR
    assert unknown_condition.type is UNKNOWN
    assert unknown_branch.type is UNKNOWN
    assert len(diagnostics) == 1


def test_typ_06_success_list_structure_uses_a_valid_promoted_type() -> None:
    """TYP-06 success: compatible numeric elements must produce ``float[]``."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).array_literal(
        (value(INTEGER), value(FLOAT)), SourceLocation(11, 1)
    )

    assert result.type == ArrayType(FLOAT)
    assert len(diagnostics) == 0


def test_typ_06_failure_list_structure_rejects_incompatible_depth() -> None:
    """TYP-06 failure: mixing an element and an array element must be rejected."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).array_literal(
        (value(INTEGER), value(ArrayType(INTEGER))), SourceLocation(11, 1)
    )

    assert result.type is ERROR
    assert len(diagnostics) == 1
    assert diagnostics.items[0].category is DiagnosticCategory.ARRAY


def test_lst_01_success_homogeneous_list_preserves_element_type() -> None:
    """LST-01 success: same-type elements must produce one array dimension."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).array_literal(
        [value(STRING), value(STRING), value(STRING)], SourceLocation(12, 1)
    )

    assert result.type == ArrayType(STRING)
    assert len(diagnostics) == 0


def test_lst_01_failure_heterogeneous_list_reports_array_diagnostic() -> None:
    """LST-01 failure: incompatible primitive elements must report one error."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).array_literal(
        [value(INTEGER), value(BOOLEAN)], SourceLocation(12, 1)
    )

    assert result.type is ERROR
    assert len(diagnostics) == 1
    assert diagnostics.items[0].category is DiagnosticCategory.ARRAY


def test_empty_and_nested_array_literals_preserve_depth() -> None:
    """An empty list is unresolved, while nested homogeneous lists retain depth."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(13, 1)

    empty = actions.array_literal([], location)
    first_row = actions.array_literal([value(INTEGER), value(INTEGER)], location)
    second_row = actions.array_literal([value(INTEGER)], location)
    matrix = actions.array_literal([first_row, second_row], location)

    assert empty.type == ArrayType(UNKNOWN)
    assert matrix.type == ArrayType(ArrayType(INTEGER))
    assert len(diagnostics) == 0


def test_array_literal_propagates_error_and_unknown_without_duplicate_diagnostics() -> None:
    """An invalid inner expression stays singular and unknown elements stay safe."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(13, 1)
    previous = actions.binary("+", value(STRING), value(INTEGER), location)

    cascaded = actions.array_literal([previous, value(INTEGER)], location)
    unresolved = actions.array_literal([value(UNKNOWN), value(INTEGER)], location)

    assert cascaded.type is ERROR
    assert unresolved.type == ArrayType(UNKNOWN)
    assert len(diagnostics) == 1


def test_nested_array_literal_collapses_compound_error_but_preserves_unknown_depth() -> None:
    """Nested recovery retains known shape only for unresolved, not invalid, types."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(13, 1)

    invalid = actions.array_literal([value(ArrayType(ERROR))], location)
    unresolved = actions.array_literal([value(ArrayType(UNKNOWN))], location)

    assert invalid.type is ERROR
    assert unresolved.type == ArrayType(ArrayType(UNKNOWN))
    assert len(diagnostics) == 0


@pytest.mark.parametrize(
    "elements",
    [
        pytest.param(
            [value(UNKNOWN), value(INTEGER), value(BOOLEAN)],
            id="direct-known-conflict",
        ),
        pytest.param(
            [
                value(ArrayType(UNKNOWN)),
                value(ArrayType(INTEGER)),
                value(ArrayType(BOOLEAN)),
            ],
            id="nested-known-conflict",
        ),
    ],
)
def test_array_unknown_does_not_hide_incompatible_known_elements(
    elements: list[SemanticValue],
) -> None:
    """A list remains invalid when its known elements already contradict."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).array_literal(
        elements, SourceLocation(13, 1)
    )

    assert result.type is ERROR
    assert len(diagnostics) == 1
    assert diagnostics.items[0].category is DiagnosticCategory.ARRAY


def test_lst_02_success_integer_index_returns_assignable_element_type() -> None:
    """LST-02 success: an integer index must expose the array's element contract."""
    diagnostics = DiagnosticBag()
    location = SourceLocation(14, 5)
    symbol = ExampleSymbol("numbers")
    container = SemanticValue(
        ArrayType(INTEGER),
        assignable=True,
        mutable=True,
        symbol=symbol,
        location=location,
    )

    result = ExpressionActions(diagnostics).index(container, value(INTEGER), location)

    assert result.type is INTEGER
    assert result.assignable is True
    assert result.mutable is True
    assert result.symbol is symbol
    assert result.location is location
    assert len(diagnostics) == 0


def test_lst_02_success_nested_array_index_removes_exactly_one_dimension() -> None:
    """LST-02 success: indexing a matrix once must leave an array row."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).index(
        value(ArrayType(ArrayType(STRING))),
        value(INTEGER),
        SourceLocation(14, 5),
    )

    assert result.type == ArrayType(STRING)
    assert len(diagnostics) == 0


@pytest.mark.parametrize(
    "index_type",
    [
        pytest.param(STRING, id="LST-02-failure-string-index"),
        pytest.param(FLOAT, id="LST-02-failure-float-index"),
        pytest.param(BOOLEAN, id="LST-02-failure-boolean-index"),
    ],
)
def test_lst_02_failure_rejects_every_known_noninteger_index(index_type: object) -> None:
    """LST-02 failure: a noninteger index must report one array diagnostic."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).index(
        value(ArrayType(INTEGER)),
        value(index_type),  # type: ignore[arg-type]
        SourceLocation(14, 5),
    )

    assert result.type is ERROR
    assert len(diagnostics) == 1
    assert diagnostics.items[0].category is DiagnosticCategory.ARRAY


def test_index_rejects_nonarray_container_and_accumulates_independent_errors() -> None:
    """Bad container and bad index must both be visible from one expression."""
    diagnostics = DiagnosticBag()

    result = ExpressionActions(diagnostics).index(
        value(STRING), value(BOOLEAN), SourceLocation(15, 1)
    )

    assert result.type is ERROR
    assert len(diagnostics) == 2
    assert all(item.category is DiagnosticCategory.ARRAY for item in diagnostics)


def test_index_propagates_error_and_unknown_without_duplicate_diagnostics() -> None:
    """Previously invalid or unresolved operands must remain recoverable."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(15, 1)
    previous = actions.binary("+", value(STRING), value(INTEGER), location)

    cascaded = actions.index(previous, value(INTEGER), location)
    unknown_container = actions.index(value(UNKNOWN), value(INTEGER), location)
    unknown_index = actions.index(value(ArrayType(INTEGER)), value(UNKNOWN), location)

    assert cascaded.type is ERROR
    assert unknown_container.type is UNKNOWN
    assert unknown_index.type is UNKNOWN
    assert len(diagnostics) == 1


def test_index_collapses_compound_error_and_preserves_known_unknown_shape() -> None:
    """Index recovery must distinguish invalid nested content from unresolved content."""
    diagnostics = DiagnosticBag()
    actions = ExpressionActions(diagnostics)
    location = SourceLocation(15, 1)

    invalid = actions.index(value(ArrayType(ArrayType(ERROR))), value(INTEGER), location)
    invalid_function = value(FunctionType((ERROR,), INTEGER))
    invalid_container = actions.index(invalid_function, value(INTEGER), location)
    invalid_index = actions.index(
        value(ArrayType(INTEGER)), invalid_function, location
    )
    unresolved = actions.index(
        value(ArrayType(ArrayType(UNKNOWN))), value(INTEGER), location
    )

    assert invalid.type is ERROR
    assert invalid_container.type is ERROR
    assert invalid_index.type is ERROR
    assert unresolved.type == ArrayType(UNKNOWN)
    assert len(diagnostics) == 0

"""Tests for immutable semantic types and compatibility rules."""

from dataclasses import FrozenInstanceError

import pytest

from src.semantic.types import (
    BOOLEAN,
    ERROR,
    FLOAT,
    INTEGER,
    NULL,
    STRING,
    UNKNOWN,
    VOID,
    ArrayType,
    ClassType,
    ErrorType,
    FunctionType,
    PrimitiveType,
    UnknownType,
    common_type,
    is_assignable,
    is_boolean,
    is_numeric,
    type_from_name,
)


def test_types_have_structural_equality_stable_representation_and_immutability() -> None:
    """Changing fields or exposing constructor syntax would break the type contract."""
    function = FunctionType([INTEGER, FLOAT], BOOLEAN)
    dog = ClassType("Dog", ClassType("Animal"))

    assert PrimitiveType("integer") == INTEGER
    assert ArrayType(ArrayType(INTEGER)) == ArrayType(ArrayType(INTEGER))
    assert function.parameter_types == (INTEGER, FLOAT)
    assert str(INTEGER) == "integer"
    assert repr(ArrayType(ArrayType(INTEGER))) == "integer[][]"
    assert repr(function) == "(integer, float) -> boolean"
    assert repr(dog) == "Dog"
    assert repr(ERROR) == "<error>"
    assert repr(UNKNOWN) == "<unknown>"
    with pytest.raises(FrozenInstanceError):
        dog.name = "Cat"  # type: ignore[misc]


def test_required_type_singletons_have_their_public_meaning() -> None:
    """Replacing a required singleton with the wrong semantic kind must fail."""
    assert (INTEGER.name, FLOAT.name, STRING.name) == ("integer", "float", "string")
    assert (BOOLEAN.name, NULL.name, VOID.name) == ("boolean", "null", "void")
    assert isinstance(ERROR, ErrorType)
    assert isinstance(UNKNOWN, UnknownType)
    assert is_numeric(INTEGER) is True
    assert is_numeric(FLOAT) is True
    assert is_numeric(BOOLEAN) is False
    assert is_boolean(BOOLEAN) is True
    assert is_boolean(INTEGER) is False


def test_helpers_honor_structurally_equal_public_type_instances() -> None:
    """Comparable instances must not change meaning merely because identity differs."""
    assert is_numeric(PrimitiveType("integer")) is True
    assert is_boolean(PrimitiveType("boolean")) is True
    assert is_assignable(ErrorType(), INTEGER) is True
    assert common_type((UnknownType(), INTEGER)) is UNKNOWN


def test_type_from_name_resolves_primitives_arrays_classes_and_unknown_names() -> None:
    """Losing depth or guessing an undeclared class would corrupt annotations."""
    animal = ClassType("Animal")
    dog = ClassType("Dog", animal)
    classes = {"Animal": animal, "Dog": dog}

    assert type_from_name("integer") is INTEGER
    assert type_from_name(" float ", array_depth=2) == ArrayType(ArrayType(FLOAT))
    assert type_from_name("Dog", class_lookup=classes) is dog
    assert type_from_name("Animal", class_lookup=classes.get) is animal
    assert type_from_name("Missing", class_lookup=classes) is UNKNOWN
    assert type_from_name("Missing") is UNKNOWN
    with pytest.raises(ValueError, match="array_depth"):
        type_from_name("integer", array_depth=-1)


def test_type_from_name_rejects_an_invalid_class_lookup_contract() -> None:
    """A malformed collaborator must fail with the API's documented error type."""
    with pytest.raises(TypeError, match="class_lookup"):
        type_from_name("Missing", class_lookup=object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("source", "target", "expected"),
    [
        pytest.param(INTEGER, INTEGER, True, id="exact-primitive"),
        pytest.param(INTEGER, FLOAT, True, id="integer-promotes-to-float"),
        pytest.param(FLOAT, INTEGER, False, id="float-does-not-narrow"),
        pytest.param(NULL, NULL, True, id="null-to-null"),
        pytest.param(NULL, STRING, False, id="null-to-string-is-conservative"),
        pytest.param(UNKNOWN, UNKNOWN, True, id="unknown-to-unknown"),
        pytest.param(UNKNOWN, INTEGER, False, id="unknown-does-not-guess"),
        pytest.param(ERROR, INTEGER, True, id="error-source-suppresses-cascade"),
        pytest.param(INTEGER, ERROR, True, id="error-target-suppresses-cascade"),
        pytest.param(
            FunctionType((INTEGER,), ERROR),
            FunctionType((INTEGER,), FLOAT),
            True,
            id="compound-error-suppresses-cascade",
        ),
        pytest.param(ArrayType(INTEGER), ArrayType(INTEGER), True, id="exact-array"),
        pytest.param(ArrayType(INTEGER), ArrayType(FLOAT), False, id="arrays-are-invariant"),
        pytest.param(ArrayType(INTEGER), ArrayType(ArrayType(INTEGER)), False, id="array-depth"),
        pytest.param(
            FunctionType((INTEGER,), FLOAT),
            FunctionType((INTEGER,), FLOAT),
            True,
            id="exact-function",
        ),
        pytest.param(
            FunctionType((INTEGER,), FLOAT),
            FunctionType((FLOAT,), FLOAT),
            False,
            id="different-function",
        ),
    ],
)
def test_is_assignable_handles_exact_promotion_structures_error_and_unknown(
    source: object,
    target: object,
    expected: bool,
) -> None:
    """An incorrect compatibility branch must be visible by its named case."""
    assert is_assignable(source, target) is expected  # type: ignore[arg-type]


def test_class_assignability_follows_declared_superclasses_only() -> None:
    """A subclass may widen to an ancestor but unrelated classes must not mix."""
    animal = ClassType("Animal")
    dog = ClassType("Dog", animal)
    poodle = ClassType("Poodle", dog)
    cat = ClassType("Cat", animal)

    assert is_assignable(poodle, animal) is True
    assert is_assignable(animal, dog) is False
    assert is_assignable(dog, cat) is False


@pytest.mark.parametrize(
    ("members", "expected"),
    [
        pytest.param([], UNKNOWN, id="empty-is-unknown"),
        pytest.param([INTEGER, INTEGER], INTEGER, id="same-type"),
        pytest.param([INTEGER, FLOAT], FLOAT, id="numeric-promotion"),
        pytest.param([UNKNOWN, INTEGER], UNKNOWN, id="unknown-propagation"),
        pytest.param(
            [UNKNOWN, INTEGER, BOOLEAN],
            ERROR,
            id="unknown-does-not-hide-known-conflict",
        ),
        pytest.param([ERROR, INTEGER], ERROR, id="error-propagation"),
        pytest.param([STRING, INTEGER], ERROR, id="incompatible-primitives"),
        pytest.param(
            [ArrayType(INTEGER), ArrayType(FLOAT)],
            ArrayType(FLOAT),
            id="array-elements-promote",
        ),
        pytest.param(
            [ArrayType(INTEGER), ArrayType(ArrayType(INTEGER))],
            ERROR,
            id="incompatible-array-depth",
        ),
        pytest.param(
            [ArrayType(UNKNOWN), ArrayType(INTEGER), ArrayType(BOOLEAN)],
            ERROR,
            id="nested-unknown-does-not-hide-known-conflict",
        ),
    ],
)
def test_common_type_is_safe_for_empty_numeric_array_error_and_unknown_inputs(
    members: list[object],
    expected: object,
) -> None:
    """A bad join must not silently assign an incompatible aggregate type."""
    assert common_type(members) == expected  # type: ignore[arg-type]


def test_common_type_uses_nearest_shared_class_and_exact_function_signatures() -> None:
    """Class joins use ancestry while distinct function signatures stay incompatible."""
    animal = ClassType("Animal")
    dog = ClassType("Dog", animal)
    poodle = ClassType("Poodle", dog)
    cat = ClassType("Cat", animal)
    first_signature = FunctionType((INTEGER,), FLOAT)
    same_signature = FunctionType((INTEGER,), FLOAT)
    other_signature = FunctionType((FLOAT,), FLOAT)

    assert common_type((poodle, dog)) == dog
    assert common_type((poodle, cat)) == animal
    assert common_type((first_signature, same_signature)) == first_signature
    assert common_type((first_signature, other_signature)) is ERROR


@pytest.mark.parametrize(
    "compound_error",
    [
        pytest.param(ArrayType(ERROR), id="error-inside-array"),
        pytest.param(
            FunctionType((INTEGER,), ERROR),
            id="error-inside-function-return",
        ),
        pytest.param(
            FunctionType((ERROR,), INTEGER),
            id="error-inside-function-parameter",
        ),
    ],
)
def test_common_type_collapses_compound_error_to_canonical_error(compound_error: object) -> None:
    """A recovery marker inside a composite must invalidate the whole join."""
    assert common_type((compound_error,)) is ERROR  # type: ignore[arg-type]


def test_common_type_checks_all_known_function_constraints_around_unknown() -> None:
    """A wildcard signature cannot hide incompatible known parameter types."""
    unknown_signature = FunctionType((UNKNOWN,), INTEGER)
    integer_signature = FunctionType((INTEGER,), INTEGER)
    boolean_signature = FunctionType((BOOLEAN,), INTEGER)

    assert common_type((unknown_signature, integer_signature)) is UNKNOWN
    assert common_type(
        (unknown_signature, integer_signature, boolean_signature)
    ) is ERROR

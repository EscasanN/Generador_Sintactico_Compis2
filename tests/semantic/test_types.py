"""Pruebas de tipos semánticos inmutables y reglas de compatibilidad."""

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
    """Cambiar campos o exponer el constructor rompería el contrato de tipos."""
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
    """Sustituir un singleton obligatorio por otro tipo semántico debe fallar."""
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
    """Las instancias comparables conservan su significado.

    La identidad concreta de cada instancia no debe modificarlo.
    """
    assert is_numeric(PrimitiveType("integer")) is True
    assert is_boolean(PrimitiveType("boolean")) is True
    assert is_assignable(ErrorType(), INTEGER) is True
    assert common_type((UnknownType(), INTEGER)) is UNKNOWN


def test_type_from_name_resolves_primitives_arrays_classes_and_unknown_names() -> None:
    """Perder profundidad o suponer una clase no declarada dañaría las anotaciones."""
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
    """Un colaborador inválido debe fallar con el tipo de error documentado."""
    with pytest.raises(TypeError, match="class_lookup"):
        type_from_name("Missing", class_lookup=object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("source", "target", "expected"),
    [
        pytest.param(INTEGER, INTEGER, True, id="exact-primitive"),
        pytest.param(INTEGER, FLOAT, True, id="integer-promotes-to-float"),
        pytest.param(FLOAT, INTEGER, False, id="float-does-not-narrow"),
        pytest.param(NULL, NULL, True, id="null-to-null"),
        pytest.param(NULL, ClassType("Node"), True, id="null-to-class-reference"),
        pytest.param(NULL, ArrayType(INTEGER), True, id="null-to-array-reference"),
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
    """Una rama de compatibilidad incorrecta debe detectarse por su caso nombrado."""
    assert is_assignable(source, target) is expected  # type: ignore[arg-type]


def test_class_assignability_follows_declared_superclasses_only() -> None:
    """Una subclase puede ampliarse a un ancestro.

    Las clases no relacionadas no deben mezclarse.
    """
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
            [ClassType("Node"), NULL],
            ClassType("Node"),
            id="nullable-class-reference",
        ),
        pytest.param(
            [ArrayType(INTEGER), NULL],
            ArrayType(INTEGER),
            id="nullable-array-reference",
        ),
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
    """Una combinación inválida no debe asignar en silencio un tipo incompatible."""
    assert common_type(members) == expected  # type: ignore[arg-type]


def test_common_type_uses_nearest_shared_class_and_exact_function_signatures() -> None:
    """Las clases usan ancestros; las firmas de función distintas son incompatibles."""
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
    """Un marcador de recuperación dentro de un compuesto invalida la combinación."""
    assert common_type((compound_error,)) is ERROR  # type: ignore[arg-type]


def test_common_type_checks_all_known_function_constraints_around_unknown() -> None:
    """Una firma comodín no oculta tipos conocidos de parámetros incompatibles."""
    unknown_signature = FunctionType((UNKNOWN,), INTEGER)
    integer_signature = FunctionType((INTEGER,), INTEGER)
    boolean_signature = FunctionType((BOOLEAN,), INTEGER)

    assert common_type((unknown_signature, integer_signature)) is UNKNOWN
    assert common_type(
        (unknown_signature, integer_signature, boolean_signature)
    ) is ERROR

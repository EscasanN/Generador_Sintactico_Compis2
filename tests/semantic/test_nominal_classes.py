"""Class compatibility follows declarations, never just their source names."""

from pathlib import Path

import pytest

from src.semantic.antlr_adapter import analyze_semantics_with_g4
from src.semantic.types import (
    ERROR, INTEGER, UNKNOWN, ArrayType, ClassType, FunctionType,
    common_type, is_assignable,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("wrap", [
    lambda type_: type_,
    ArrayType,
    lambda type_: FunctionType((type_,), INTEGER),
    lambda type_: FunctionType((), type_),
])
def test_homonymous_declarations_are_incompatible_in_every_type_position(wrap):
    first = ClassType("A")
    second = ClassType("A")
    left, right = wrap(first), wrap(second)

    assert not is_assignable(left, right)
    assert not is_assignable(right, left)
    assert common_type((left, right)) is ERROR
    assert common_type((UNKNOWN, left, right)) is ERROR
    assert len({left, right}) == 2
    assert {left: "first", right: "second"}[wrap(first)] == "first"


def test_subclass_does_not_widen_to_a_homonymous_unrelated_base():
    outer = ClassType("A")
    inner = ClassType("A")
    child = ClassType("B", inner)

    assert is_assignable(child, inner)
    assert not is_assignable(child, outer)
    assert common_type((child, outer)) is ERROR


def test_repeated_references_and_real_ancestry_keep_their_nominal_compatibility():
    base = ClassType("A")
    child = ClassType("B", base)

    assert is_assignable(child, base)
    assert common_type((child, base)) is base
    assert is_assignable(ArrayType(base), ArrayType(base))
    assert is_assignable(FunctionType((base,), base), FunctionType((base,), base))
    assert not is_assignable(ArrayType(child), ArrayType(base))


@pytest.mark.parametrize("return_type,body", [
    ("integer", "outer=new B(); return outer.x;"),
    ("integer", "return consume(new B());"),
    ("A", "return new B();"),
    ("integer", "let values:A[]=[outer,new B()]; return 1;"),
    ("integer", "let mixed=true ? outer : new B(); return 1;"),
    ("integer", "let callable=consume; callable=localConsume; return 1;"),
])
def test_frontend_rejects_values_crossing_homonymous_class_boundaries(return_type, body):
    source = (
        "class A { let x:integer=1; } "
        "function consume(value:A):integer { return value.x; } "
        f"function f():{return_type} {{ let outer:A=new A(); "
        "class A { let y:string=\"bad\"; } class B:A {} "
        "function localConsume(value:A):integer { return 1; } "
        f"{body} }} let r=f();"
    )
    run = analyze_semantics_with_g4(
        ROOT / "src/compiscript/grammar/Compiscript.g4", source,
        ROOT / "semantic_profiles/compiscript.semantic.json", "program",
    )
    assert run.syntax_result.accepted
    assert run.semantic_result is not None
    assert not run.semantic_result.accepted
    assert run.semantic_result.diagnostics

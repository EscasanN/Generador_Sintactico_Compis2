from src.antlr_mode.parse_tree import ParseTreeNode
from src.semantic.actions.classes import (
    access_member,
    construct,
    declare_class,
    declare_field,
    declare_method,
    enter_class,
    exit_class,
    this_value,
)
from src.semantic.evaluator import SemanticContext
from src.semantic.symbol_table import ScopeKind
from src.semantic.types import ERROR, INTEGER, STRING, VOID
from src.semantic.values import SemanticValue


def node(text="class", line=1):
    return ParseTreeNode(text, text=text, line=line, column=1)


def build_class(context: SemanticContext, with_constructor=True):
    class_value = declare_class(context, node(), "Box")
    enter_class(context, node(), class_value)
    field = declare_field(context, node(), "value", INTEGER)
    method = declare_method(context, node(), "get", (), INTEGER)
    if with_constructor:
        declare_method(
            context,
            node(),
            "constructor",
            (INTEGER,),
            VOID,
            ("initial",),
            constructor=True,
        )
    return class_value, field, method


def test_cls_01_success_declared_field_and_method_are_accessible():
    context = SemanticContext()
    class_value, field, method = build_class(context)
    exit_class(context, node())
    instance = SemanticValue(class_value.type)
    assert access_member(context, node(), instance, "value").symbol is field.symbol
    assert access_member(context, node(), instance, "get").symbol is method.symbol


def test_cls_01_failure_missing_member_is_reported():
    context = SemanticContext()
    class_value, _, _ = build_class(context)
    exit_class(context, node())
    assert access_member(
        context, node(), SemanticValue(class_value.type), "missing"
    ).type == ERROR


def test_cls_02_success_constructor_accepts_matching_arguments():
    context = SemanticContext()
    class_value, _, _ = build_class(context)
    exit_class(context, node())
    result = construct(context, node(), class_value, (SemanticValue(INTEGER),))
    assert result.type == class_value.type


def test_cls_02_failure_constructor_arguments_have_wrong_types():
    context = SemanticContext()
    with_constructor, _, _ = build_class(context)
    exit_class(context, node())
    assert construct(
        context, node(), with_constructor, (SemanticValue(STRING),)
    ).type == ERROR



def test_cls_02_success_implicit_constructor_accepts_no_arguments():
    """A class without an explicit constructor still has a zero-arity one."""
    context = SemanticContext()
    empty = declare_class(context, node(), "Empty")

    result = construct(context, node(), empty, ())

    assert result.type == empty.type
    assert not context.diagnostics.has_errors


def test_cls_02_failure_implicit_constructor_rejects_arguments():
    """Arguments must not be silently discarded by an implicit constructor."""
    context = SemanticContext()
    empty = declare_class(context, node(), "Empty")

    result = construct(context, node(), empty, (SemanticValue(INTEGER),))

    assert result.type == ERROR
    assert context.diagnostics.has_errors


def test_cls_03_success_this_inside_class():
    context = SemanticContext()
    class_value = declare_class(context, node(), "Owner")
    enter_class(context, node(), class_value)
    assert this_value(context, node()).type == class_value.type
    exit_class(context, node())


def test_cls_03_failure_this_outside_class():
    context = SemanticContext()
    assert this_value(context, node()).type == ERROR
    assert context.diagnostics.has_errors


def test_member_lookup_keeps_the_original_base_after_name_shadowing():
    context = SemanticContext()
    base = declare_class(context, node(), "Base")
    enter_class(context, node(), base)
    field = declare_field(context, node(), "value", INTEGER)
    exit_class(context, node())
    child = declare_class(context, node(), "Child", base)
    context.symbol_table.enter_scope(ScopeKind.BLOCK, "inner")
    shadow = declare_class(context, node(), "Base")
    enter_class(context, node(), shadow)
    declare_field(context, node(), "value", STRING)
    exit_class(context, node())

    inherited = access_member(context, node(), SemanticValue(child.type), "value")

    assert inherited.symbol is field.symbol
    assert inherited.type == INTEGER


def test_class_type_resolution_restores_the_outer_class_after_leaving_scope():
    context = SemanticContext()
    outer = declare_class(context, node(), "Base")
    context.symbol_table.enter_scope(ScopeKind.BLOCK, "inner")
    inner = declare_class(context, node(), "Base")
    assert context.resolve_type("Base") is inner.type
    context.symbol_table.exit_scope()

    assert context.resolve_type("Base") is outer.type

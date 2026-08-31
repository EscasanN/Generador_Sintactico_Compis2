from src.parser.parse_tree import ParseTreeNode
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


def test_cls_02_failure_constructor_missing_or_arguments_wrong():
    context = SemanticContext()
    with_constructor, _, _ = build_class(context)
    exit_class(context, node())
    assert construct(
        context, node(), with_constructor, (SemanticValue(STRING),)
    ).type == ERROR

    other = declare_class(context, node(), "Empty")
    assert construct(context, node(), other, ()).type == ERROR


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

from src.parser.parse_tree import ParseTreeNode
from src.semantic.actions.callables import (
    call_function,
    declare_function,
    enter_function,
    exit_function,
    return_value,
)
from src.semantic.actions.declarations import declare_variable, resolve_identifier
from src.semantic.evaluator import SemanticContext
from src.semantic.types import BOOLEAN, ERROR, INTEGER
from src.semantic.values import SemanticValue


def node(text="callable", line=1):
    return ParseTreeNode(text, text=text, line=line, column=1)


def test_fun_01_success_call_matches_argument_count_and_types():
    context = SemanticContext()
    function = declare_function(context, node(), "f", (INTEGER, BOOLEAN), INTEGER)
    result = call_function(
        context,
        node(),
        function,
        (SemanticValue(INTEGER), SemanticValue(BOOLEAN)),
    )
    assert result.type == INTEGER
    assert not context.diagnostics.has_errors


def test_fun_01_failure_call_rejects_wrong_count_and_positional_type():
    context = SemanticContext()
    function = declare_function(context, node(), "f", (INTEGER,), INTEGER)
    assert call_function(context, node(line=2), function, ()).type == ERROR
    assert call_function(
        context, node(line=3), function, (SemanticValue(BOOLEAN),)
    ).type == ERROR
    assert len(context.diagnostics) == 2


def test_fun_02_success_return_matches_declared_type():
    context = SemanticContext()
    function = declare_function(context, node(), "f", (), INTEGER)
    enter_function(context, node(), function)
    return_value(context, node(), SemanticValue(INTEGER))
    exit_function(context, node())
    assert not context.diagnostics.has_errors


def test_fun_02_failure_return_type_is_incompatible():
    context = SemanticContext()
    function = declare_function(context, node(), "f", (), INTEGER)
    enter_function(context, node(), function)
    return_value(context, node(), SemanticValue(BOOLEAN))
    exit_function(context, node())
    assert context.diagnostics.has_errors


def test_fun_03_success_function_is_visible_for_recursion_before_body():
    context = SemanticContext()
    function = declare_function(context, node(), "factorial", (INTEGER,), INTEGER)
    enter_function(context, node(), function)
    recursive = resolve_identifier(context, node("factorial"))
    assert recursive.symbol is function.symbol
    exit_function(context, node())


def test_fun_03_failure_missing_recursive_symbol_is_reported():
    context = SemanticContext()
    assert resolve_identifier(context, node("factorial")).type == ERROR


def test_fun_04_success_nested_function_captures_definition_scope():
    context = SemanticContext()
    outer = declare_function(context, node(), "outer", (), INTEGER)
    enter_function(context, node(), outer)
    captured = declare_variable(context, node(), "captured", INTEGER)
    inner = declare_function(context, node(), "inner", (), INTEGER)
    assert inner.symbol.metadata["definition_scope"] is context.symbol_table.current_scope
    assert resolve_identifier(context, node("captured")).symbol is captured.symbol
    exit_function(context, node())


def test_fun_04_failure_closure_cannot_capture_nonexistent_name():
    context = SemanticContext()
    outer = declare_function(context, node(), "outer", (), INTEGER)
    enter_function(context, node(), outer)
    assert resolve_identifier(context, node("absent")).type == ERROR
    exit_function(context, node())


def test_fun_05_success_distinct_functions_share_a_scope():
    context = SemanticContext()
    declare_function(context, node(), "first", (), INTEGER)
    declare_function(context, node(), "second", (), INTEGER)
    assert not context.diagnostics.has_errors


def test_fun_05_failure_duplicate_function_name_is_rejected():
    context = SemanticContext()
    declare_function(context, node(), "same", (), INTEGER)
    assert declare_function(context, node(), "same", (), INTEGER).type == ERROR

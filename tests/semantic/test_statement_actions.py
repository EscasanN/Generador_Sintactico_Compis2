from src.parser.parse_tree import ParseTreeNode
from src.semantic.actions.declarations import (
    declare_constant,
    declare_parameter,
    declare_variable,
    resolve_identifier,
)
from src.semantic.evaluator import SemanticContext
from src.semantic.types import ERROR, INTEGER
from src.semantic.values import SemanticValue


def node(text="declaration", line=1):
    return ParseTreeNode(text, text=text, line=line, column=1)


def test_typ_05_success_constant_has_a_compatible_initializer():
    context = SemanticContext()
    value = declare_constant(
        context, node(), "answer", INTEGER, SemanticValue(INTEGER)
    )
    assert value.type == INTEGER
    assert not value.mutable
    assert not context.diagnostics.has_errors


def test_typ_05_failure_constant_without_initializer_is_reported():
    context = SemanticContext()
    declare_constant(context, node(), "answer", INTEGER)
    assert context.diagnostics.has_errors
    assert "must be initialized" in context.diagnostics.items[0].message


def test_declaration_and_resolution_actions_use_the_symbol_table_contract():
    context = SemanticContext()
    declared = declare_variable(context, node(), "value", INTEGER)
    resolved = resolve_identifier(context, node("value"))
    assert resolved.symbol is declared.symbol
    assert resolved.assignable and resolved.mutable


def test_duplicate_variable_and_parameter_actions_accumulate_errors():
    context = SemanticContext()
    declare_variable(context, node(line=1), "same", INTEGER)
    assert declare_variable(context, node(line=2), "same", INTEGER).type == ERROR
    declare_parameter(context, node(line=3), "arg", INTEGER)
    assert declare_parameter(context, node(line=4), "arg", INTEGER).type == ERROR
    assert len(context.diagnostics) == 2


def test_undeclared_identifier_returns_recovery_value_without_throwing():
    context = SemanticContext()
    result = resolve_identifier(context, node("missing"))
    assert result.type == ERROR
    assert len(context.diagnostics) == 1

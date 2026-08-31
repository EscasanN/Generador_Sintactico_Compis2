from src.parser.parse_tree import ParseTreeNode
from src.semantic.actions.control_flow import FlowSignal, validate_sequence
from src.semantic.actions.declarations import declare_parameter, declare_variable
from src.semantic.diagnostics import DiagnosticSeverity
from src.semantic.evaluator import SemanticContext
from src.semantic.types import ERROR, INTEGER


def node(line=1, children=()):
    return ParseTreeNode("node", list(children), line=line, column=1)


def test_gen_01_success_sequence_without_transfer_has_no_dead_code():
    context = SemanticContext()
    assert validate_sequence(context, node(), (None, None)) is None
    assert len(context.diagnostics) == 0


def test_gen_01_failure_instruction_after_return_is_reported_as_dead_code():
    context = SemanticContext()
    tree = node(children=(node(1), node(2)))
    assert validate_sequence(context, tree, (FlowSignal.RETURN, None)) is FlowSignal.RETURN
    diagnostic = context.diagnostics.items[0]
    assert "unreachable" in diagnostic.message
    assert diagnostic.location.line == 2
    assert diagnostic.severity is DiagnosticSeverity.WARNING


def test_gen_03_success_distinct_variables_and_parameters_are_accepted():
    context = SemanticContext()
    declare_variable(context, node(), "left", INTEGER)
    declare_parameter(context, node(), "right", INTEGER)
    assert not context.diagnostics.has_errors


def test_gen_03_failure_duplicate_variables_and_parameters_are_rejected():
    context = SemanticContext()
    declare_variable(context, node(1), "value", INTEGER)
    assert declare_variable(context, node(2), "value", INTEGER).type == ERROR
    declare_parameter(context, node(3), "parameter", INTEGER)
    assert declare_parameter(context, node(4), "parameter", INTEGER).type == ERROR
    assert len(context.diagnostics) == 2


def test_multiple_independent_semantic_errors_accumulate_in_one_context():
    context = SemanticContext()
    declare_variable(context, node(1), "same", INTEGER)
    declare_variable(context, node(2), "same", INTEGER)
    declare_parameter(context, node(3), "arg", INTEGER)
    declare_parameter(context, node(4), "arg", INTEGER)
    assert len(context.diagnostics) == 2

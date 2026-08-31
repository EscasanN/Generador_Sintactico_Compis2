import pytest

from src.parser.parse_tree import ParseTreeNode
from src.semantic.actions.callables import (
    declare_function,
    enter_function,
    exit_function,
    return_value,
)
from src.semantic.actions.control_flow import (
    FlowSignal,
    break_loop,
    continue_loop,
    enter_loop,
    exit_loop,
    require_boolean_condition,
)
from src.semantic.evaluator import SemanticContext
from src.semantic.types import BOOLEAN, ERROR, INTEGER
from src.semantic.values import SemanticValue


def node(line=1):
    return ParseTreeNode("control", line=line, column=1)


@pytest.mark.parametrize("construct", ["if", "while", "do-while", "for", "switch"])
def test_ctl_01_success_every_required_condition_accepts_boolean(construct):
    context = SemanticContext()
    result = require_boolean_condition(
        context, node(), SemanticValue(BOOLEAN), construct
    )
    assert result.type == BOOLEAN
    assert not context.diagnostics.has_errors


@pytest.mark.parametrize("construct", ["if", "while", "do-while", "for", "switch"])
def test_ctl_01_failure_every_required_condition_rejects_nonboolean(construct):
    context = SemanticContext()
    result = require_boolean_condition(
        context, node(), SemanticValue(INTEGER), construct
    )
    assert result.type == ERROR
    assert context.diagnostics.has_errors


def test_ctl_02_success_break_and_continue_inside_loop():
    context = SemanticContext()
    enter_loop(context, node())
    assert break_loop(context, node()) is FlowSignal.BREAK
    assert continue_loop(context, node()) is FlowSignal.CONTINUE
    exit_loop(context, node())
    assert not context.diagnostics.has_errors


def test_ctl_02_failure_break_and_continue_outside_loop():
    context = SemanticContext()
    assert break_loop(context, node()) is None
    assert continue_loop(context, node()) is None
    assert len(context.diagnostics) == 2


def test_ctl_03_success_return_inside_function():
    context = SemanticContext()
    function = declare_function(context, node(), "f", (), INTEGER)
    enter_function(context, node(), function)
    assert return_value(context, node(), SemanticValue(INTEGER)) is FlowSignal.RETURN
    exit_function(context, node())


def test_ctl_03_failure_return_outside_function():
    context = SemanticContext()
    assert return_value(context, node(), SemanticValue(INTEGER)).type == ERROR
    assert context.diagnostics.has_errors

"""Structured control flow lowered to labels and jumps (block 3).

Mixed into ``CompiscriptCodeGenerator``. The templates follow ``DISENO_TAC.md``.
A value that crosses a branch (condition, switch discriminant, foreach state)
stays live until the join label and is released there, so no path reads a
recycled temporary (CTL-01…CTL-08, LST-04, EXT-07).

Loop destinations:

=========  ==========  ======================
loop       break       continue
=========  ==========  ======================
while      exit        condition
do-while   exit        final condition
for        exit        update
foreach    exit        index increment
=========  ==========  ======================

``switch`` pushes no destination: as in the semantic phase, ``break`` and
``continue`` belong to the nearest enclosing loop and cases fall through.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from src.antlr_mode.parse_tree import ParseTreeNode
from src.codegen.contracts import CodegenError, ValueRef
from src.codegen.ir import OpCode, Operand, OperandKind
from src.semantic.types import BOOLEAN, INTEGER

_FOR_WITH_CONDITION = frozenset({"ForCondNoUpdate", "ForCondUpdate"})
_FOR_WITH_UPDATE = frozenset({"ForNoCondUpdate", "ForCondUpdate"})


class ControlFlowLowering:
    """if/else, loops, switch, break/continue and try/catch."""

    STATEMENTS = {
        "ifStatement": "lower_if",
        "whileStatement": "lower_while",
        "doWhileStatement": "lower_do_while",
        "forStatement": "lower_for",
        "foreachStatement": "lower_foreach",
        "switchStatement": "lower_switch",
        "breakStatement": "lower_break",
        "continueStatement": "lower_continue",
        "tryCatchStatement": "lower_try_catch",
    }

    @contextmanager
    def loop_targets(self, exit_label: Operand, continue_label: Operand) -> Iterator[None]:
        """Push a loop's destinations; they are popped even if lowering fails."""
        self.break_targets.append(exit_label)
        self.continue_targets.append(continue_label)
        try:
            yield
        finally:
            self.break_targets.pop()
            self.continue_targets.pop()

    # -- conditionals ------------------------------------------------------------

    def lower_if(self, node: ParseTreeNode) -> None:
        location = self.location(node)
        blocks = self.children(node, "block")
        condition = self.lower_expression(self.child(node, "expression"))
        labels = self.builder.labels
        otherwise = labels.next("if_else") if len(blocks) == 2 else None
        end = labels.next("if_end")
        otherwise = otherwise or end
        self.branch_false(condition.operand, otherwise, location)
        self.lower_block(blocks[0])
        if len(blocks) == 2:
            self.jump(end, location)
            self.mark(otherwise, location)
            self.lower_block(blocks[1])
        self.mark(end, location)
        self.settle(condition, location)

    def lower_switch(self, node: ParseTreeNode) -> None:
        """Evaluate the discriminant once, dispatch in source order, fall through."""
        location = self.location(node)
        labels = self.builder.labels
        discriminant = self.expressions.snapshot(
            self.lower_expression(self.child(node, "expression")), location
        )
        cases = [(case, labels.next("switch_case")) for case in self.children(node, "switchCase")]
        default = self.child(node, "defaultCase")
        default_label = labels.next("switch_default") if default is not None else None
        end = labels.next("switch_end")
        matched: ValueRef | None = None
        for case, label in cases:
            case_location = self.location(case)
            value = self.lower_expression(self.child(case, "expression"))
            if matched is None:
                matched = ValueRef(
                    self.builder.temporary(BOOLEAN), BOOLEAN, True, case_location
                )
            self.builder.emit(
                OpCode.EQ, discriminant.operand, value.operand, matched.operand, case_location
            )
            value.release(self.builder, case_location)
            self.branch_true(matched.operand, label, case_location)
        self.jump(default_label or end, location)
        for case, label in cases:
            self.mark(label, self.location(case))
            self._lower_statements(case)
        if default is not None and default_label is not None:
            self.mark(default_label, self.location(default))
            self._lower_statements(default)
        self.mark(end, location)
        self.settle(matched, location)
        self.settle(discriminant, location)

    def _lower_statements(self, node: ParseTreeNode) -> None:
        for statement in self.children(node, "statement"):
            self.lower_statement(statement)

    # -- loops -------------------------------------------------------------------

    def lower_while(self, node: ParseTreeNode) -> None:
        location = self.location(node)
        condition_label = self.builder.labels.next("while_cond")
        end = self.builder.labels.next("while_end")
        self.mark(condition_label, location)
        condition = self.lower_expression(self.child(node, "expression"))
        self.branch_false(condition.operand, end, location)
        with self.loop_targets(end, condition_label):
            self.lower_block(self.child(node, "block"))
        self.jump(condition_label, location)
        self.mark(end, location)
        self.settle(condition, location)

    def lower_do_while(self, node: ParseTreeNode) -> None:
        location = self.location(node)
        labels = self.builder.labels
        body = labels.next("do_body")
        condition_label = labels.next("do_cond")
        end = labels.next("do_end")
        self.mark(body, location)
        with self.loop_targets(end, condition_label):
            self.lower_block(self.child(node, "block"))
        if self.mark(condition_label, location):
            condition = self.lower_expression(self.child(node, "expression"))
            self.branch_true(condition.operand, body, location)
            condition.release(self.builder, location)
        self.mark(end, location)

    def lower_for(self, node: ParseTreeNode) -> None:
        """The four grammar forms: condition and update are each optional (CTL-05)."""
        location = self.location(node)
        labels = self.builder.labels
        initializer = self.child(node, "forInit")
        for statement in self.rule_children(initializer) if initializer else ():
            self.lower_statement(statement)
        expressions = self.children(node, "expression")
        condition_node = expressions[0] if node.alternative in _FOR_WITH_CONDITION else None
        update_node = expressions[-1] if node.alternative in _FOR_WITH_UPDATE else None
        condition_label = labels.next("for_cond")
        update = labels.next("for_update")
        end = labels.next("for_end")
        self.mark(condition_label, location)
        condition: ValueRef | None = None
        if condition_node is not None:
            condition = self.lower_expression(condition_node)
            self.branch_false(condition.operand, end, location)
        with self.loop_targets(end, update):
            self.lower_block(self.child(node, "block"))
        if self.mark(update, location):
            if update_node is not None:
                self.lower_expression(update_node).release(self.builder, location)
            self.jump(condition_label, location)
        self.mark(end, location)
        self.settle(condition, location)

    def lower_foreach(self, node: ParseTreeNode) -> None:
        """Indexed traversal: list_len once, list_get per element (LST-04, EXT-04)."""
        location = self.location(node)
        labels = self.builder.labels
        builder = self.builder
        iterator = self.declared_symbol(node)
        items = self.expressions.snapshot(
            self.lower_expression(self.child(node, "expression")), location
        )
        length = ValueRef(builder.temporary(INTEGER), INTEGER, True, location)
        builder.emit(OpCode.LIST_LEN, items.operand, result=length.operand, location=location)
        index = ValueRef(builder.temporary(INTEGER), INTEGER, True, location)
        builder.emit(
            OpCode.COPY, Operand(OperandKind.CONSTANT, 0, INTEGER),
            result=index.operand, location=location,
        )
        condition_label = labels.next("foreach_cond")
        step = labels.next("foreach_next")
        end = labels.next("foreach_end")
        self.mark(condition_label, location)
        inside = ValueRef(builder.temporary(BOOLEAN), BOOLEAN, True, location)
        builder.emit(OpCode.LT, index.operand, length.operand, inside.operand, location)
        self.branch_false(inside.operand, end, location)
        self.emit_into_symbol(
            node, iterator, OpCode.LIST_GET, items.operand, index.operand, location
        )
        with self.loop_targets(end, step):
            self.lower_block(self.child(node, "block"))
        if self.mark(step, location):
            builder.emit(
                OpCode.ADD, index.operand, Operand(OperandKind.CONSTANT, 1, INTEGER),
                index.operand, location,
            )
            self.jump(condition_label, location)
        self.mark(end, location)
        for value in (inside, index, length, items):
            self.settle(value, location)

    def lower_break(self, node: ParseTreeNode) -> None:
        if not self.break_targets:
            raise CodegenError(
                "IRGEN-BREAK-OUTSIDE-LOOP", "break has no enclosing loop", self.location(node)
            )
        self.jump(self.break_targets[-1], self.location(node))

    def lower_continue(self, node: ParseTreeNode) -> None:
        if not self.continue_targets:
            raise CodegenError(
                "IRGEN-CONTINUE-OUTSIDE-LOOP",
                "continue has no enclosing loop",
                self.location(node),
            )
        self.jump(self.continue_targets[-1], self.location(node))

    # -- exceptions --------------------------------------------------------------

    def lower_try_catch(self, node: ParseTreeNode) -> None:
        """High-level handler IR: try_begin, try_end and catch (EXT-07)."""
        location = self.location(node)
        protected, handler = self.children(node, "block")
        variable = self.declared_symbol(node)
        catch = self.builder.labels.next("try_catch")
        end = self.builder.labels.next("try_end")
        self.target(catch)
        self.builder.emit(OpCode.TRY_BEGIN, result=catch, location=location)
        self.lower_block(protected)
        if self.reachable:
            self.builder.emit(OpCode.TRY_END, location=location)
        self.jump(end, location)
        self.mark(catch, location)
        self.emit_into_symbol(node, variable, OpCode.CATCH, None, None, location)
        self.lower_block(handler)
        self.mark(end, location)

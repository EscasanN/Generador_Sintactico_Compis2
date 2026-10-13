"""Lower a whole analysed Compiscript program to structured TAC (block 3).

``CompiscriptCodeGenerator`` walks the common ``ParseTreeNode`` tree of an
accepted program. Statement handlers live in mixins (``statements``,
``control_flow``); expressions go through ``ProgramExpressionLowerer``, which
extends Daniel's ``ExpressionLowerer`` only for the alternatives owned by this
block and delegates everything else unchanged.

Every reached statement or expression alternative has a handler; anything else
raises ``CodegenError("IRGEN-UNSUPPORTED-NODE")`` with its source location so a
program is never accepted with partial TAC (EXT-08).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.antlr_mode.parse_tree import ParseTreeNode
from src.codegen.activation import RuntimeLayouts
from src.codegen.builder import IRBuilder
from src.codegen.contracts import CodegenError, ValueRef
from src.codegen.control_flow import ControlFlowLowering
from src.codegen.expression_lowering import ExpressionLowerer
from src.codegen.ir import IRProgram, Operand
from src.codegen.semantic_facts import SemanticFactsIndex
from src.codegen.statements import StatementLowering
from src.semantic.diagnostics import SourceLocation
from src.semantic.symbol_table import Symbol
from src.semantic.values import SemanticValue


@dataclass(frozen=True, slots=True)
class GeneratedProgram:
    """The lowered program and the layouts with its temporary slots reserved."""

    program: IRProgram
    layouts: RuntimeLayouts
    global_temporary_peak: int


class ProgramExpressionLowerer(ExpressionLowerer):
    """Daniel's lowerer plus the expression alternatives handled by block 3.

    ``lower`` is the single entry point and Daniel's helpers recurse through it,
    so nested nodes reach the block-3 handlers as well.
    """

    def __init__(self, generator: "CompiscriptCodeGenerator") -> None:
        super().__init__(generator.builder, generator.facts)
        self.generator = generator

    def lower(self, node: ParseTreeNode) -> ValueRef:
        handler = self.generator.EXPRESSIONS.get(node.alternative or "")
        if handler is not None:
            return getattr(self.generator, handler)(node)
        return super().lower(node)

    def lower_default(self, node: ParseTreeNode) -> ValueRef:
        """Daniel's lowering for a node that needs no block-3 treatment."""
        return super().lower(node)


class CompiscriptCodeGenerator(ControlFlowLowering, StatementLowering):
    """Coordinate facts, layouts, the IR builder and the control stacks."""

    STATEMENTS: dict[str, str] = {
        **StatementLowering.STATEMENTS,
        **ControlFlowLowering.STATEMENTS,
    }
    EXPRESSIONS: dict[str, str] = {
        **StatementLowering.EXPRESSIONS,
    }

    def __init__(self, facts: SemanticFactsIndex) -> None:
        self.facts = facts
        self.layouts = facts.layouts
        self.builder = IRBuilder()
        self.expressions = ProgramExpressionLowerer(self)
        self.break_targets: list[Operand] = []
        self.continue_targets: list[Operand] = []
        self.function_stack: list[object] = []
        self.class_stack: list[object] = []
        self.reachable = True
        self._targeted: set[str] = set()
        self._used = False

    # -- entry point -------------------------------------------------------------

    def generate(self, root: ParseTreeNode) -> GeneratedProgram:
        """Lower global code, then every procedure, and reserve temporary slots."""
        if self._used:
            raise RuntimeError("a generator lowers exactly one program")
        self._used = True
        for statement in self.rule_children(root):
            self.lower_statement(statement)
        global_peak = self.builder.temporaries.peak_active
        program = self.builder.build()
        layouts = self.layouts.with_temporary_peaks({}, global_peak)
        return GeneratedProgram(program, layouts, global_peak)

    # -- dispatch ----------------------------------------------------------------

    def lower_statement(self, node: ParseTreeNode) -> None:
        """Lower one statement; code after a terminal transfer is not emitted."""
        if not self.reachable:
            return
        target = node
        while target.rule_name == "statement":
            (target,) = self.rule_children(target)
        handler = self.STATEMENTS.get(target.alternative or "") or self.STATEMENTS.get(
            target.rule_name or ""
        )
        if handler is None:
            raise CodegenError(
                "IRGEN-UNSUPPORTED-NODE",
                f"unsupported statement {target.alternative or target.rule_name}",
                self.location(target),
            )
        getattr(self, handler)(target)

    def lower_expression(self, node: ParseTreeNode) -> ValueRef:
        return self.expressions.lower(node)

    # -- reachability ------------------------------------------------------------

    def jump(self, label: Operand, location: SourceLocation) -> None:
        if self.reachable:
            self._targeted.add(str(label.value))
            self.builder.jump(label, location)
            self.reachable = False

    def branch_false(self, condition: Operand, label: Operand, location: SourceLocation) -> None:
        self._targeted.add(str(label.value))
        self.builder.branch_false(condition, label, location)

    def branch_true(self, condition: Operand, label: Operand, location: SourceLocation) -> None:
        self._targeted.add(str(label.value))
        self.builder.branch_true(condition, label, location)

    def target(self, label: Operand) -> None:
        """Record a transfer to ``label`` not emitted through ``jump``/``branch``."""
        self._targeted.add(str(label.value))

    def mark(self, label: Operand, location: SourceLocation) -> bool:
        """Define ``label`` when control can reach it; return the new reachability."""
        if self.reachable or str(label.value) in self._targeted:
            self.builder.mark(label, location)
            self.reachable = True
        return self.reachable

    def settle(self, value: ValueRef | None, location: SourceLocation) -> None:
        """Release a value held across branches once the join point is known.

        A reachable join emits ``release``; an unreachable one drops the lease
        silently, since no path reads the value there.
        """
        if value is None or not value.owns_temporary:
            return
        if self.reachable:
            value.release(self.builder, location)
        else:
            self.builder.temporaries.release(value.operand)

    # -- tree and fact helpers ---------------------------------------------------

    @staticmethod
    def rule_children(node: ParseTreeNode) -> list[ParseTreeNode]:
        return [child for child in node.children if child.rule_name is not None]

    def child(self, node: ParseTreeNode, rule: str) -> ParseTreeNode | None:
        return next((c for c in node.children if c.rule_name == rule), None)

    def children(self, node: ParseTreeNode, rule: str) -> list[ParseTreeNode]:
        return [c for c in node.children if c.rule_name == rule]

    def location(self, node: ParseTreeNode) -> SourceLocation:
        if node.line is None or node.column is None:
            raise CodegenError(
                "IRGEN-MISSING-LOCATION", f"{node.rule_name} has no source coordinates"
            )
        return SourceLocation(node.line, node.column, node.end_line, node.end_column)

    def fact(self, node: ParseTreeNode) -> SemanticValue:
        try:
            return self.facts.value_for(node)
        except LookupError as error:
            raise CodegenError(
                "IRGEN-MISSING-FACT", "missing SemanticValue", self.location(node)
            ) from error

    def declared_symbol(self, node: ParseTreeNode) -> Symbol:
        """The Symbol semantics recorded on ``node`` (declaration or resolution)."""
        symbol = self.facts.symbol_for(node)
        if symbol is None:
            raise CodegenError(
                "IRGEN-MISSING-SYMBOL", "missing resolved Symbol", self.location(node)
            )
        return symbol

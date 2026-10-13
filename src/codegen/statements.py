"""Declarations, assignments, expression statements and print (block 3).

Mixed into ``CompiscriptCodeGenerator``; relies on its ``builder``, ``facts``,
``expressions`` and tree helpers. Implicit int→float conversions accepted by the
semantic phase are made explicit here: constants are converted at compile time
and other values with ``t = cast float v``.
"""

from __future__ import annotations

from src.antlr_mode.parse_tree import ParseTreeNode
from src.codegen.contracts import ValueRef
from src.codegen.ir import OpCode, Operand, OperandKind
from src.semantic.diagnostics import SourceLocation
from src.semantic.symbol_table import Symbol
from src.semantic.types import FLOAT, INTEGER, Type

PRINT_LABEL = "print"

_NUMERIC_BINARY: dict[str, OpCode] = {
    "AddExpr": OpCode.ADD, "SubExpr": OpCode.SUB,
    "MulExpr": OpCode.MUL, "DivExpr": OpCode.DIV, "ModExpr": OpCode.MOD,
    "EqualsExpr": OpCode.EQ, "NotEqualsExpr": OpCode.NE,
    "LessExpr": OpCode.LT, "LessEqualExpr": OpCode.LE,
    "GreaterExpr": OpCode.GT, "GreaterEqualExpr": OpCode.GE,
}


class StatementLowering:
    """Straight-line statements and the int→float coercion rule."""

    STATEMENTS = {
        "variableDeclaration": "lower_declaration",
        "constantDeclaration": "lower_declaration",
        "SimpleAssignment": "lower_simple_assignment",
        "expressionStatement": "lower_expression_statement",
        "printStatement": "lower_print",
        "block": "lower_block",
    }
    EXPRESSIONS = {alternative: "lower_numeric_binary" for alternative in _NUMERIC_BINARY}

    # -- statements --------------------------------------------------------------

    def lower_block(self, node: ParseTreeNode) -> None:
        for statement in self.children(node, "statement"):
            self.lower_statement(statement)

    def lower_declaration(self, node: ParseTreeNode) -> None:
        """``let``/``const`` with an initializer copies it; without one emits nothing."""
        symbol = self.declared_symbol(node)
        initializer = self.child(node, "initializer")
        expression = self.child(initializer or node, "expression")
        if expression is None:
            return
        location = self.location(node)
        value = self.coerce(self.lower_expression(expression), symbol.type, location)
        self.store_symbol(node, symbol, value, location)
        value.release(self.builder, location)

    def lower_simple_assignment(self, node: ParseTreeNode) -> None:
        """``x = e;``: semantics records the target Symbol on the statement node."""
        symbol = self.declared_symbol(node)
        location = self.location(node)
        expression = self.child(node, "expression")
        assert expression is not None
        value = self.coerce(self.lower_expression(expression), symbol.type, location)
        self.store_symbol(node, symbol, value, location)
        value.release(self.builder, location)

    def lower_expression_statement(self, node: ParseTreeNode) -> None:
        expression = self.child(node, "expression")
        assert expression is not None
        value = self.lower_expression(expression)
        value.release(self.builder, self.location(node))

    def lower_print(self, node: ParseTreeNode) -> None:
        """``print(e)`` calls the abstract runtime procedure ``print`` (EXT-01)."""
        location = self.location(node)
        expression = self.child(node, "expression")
        assert expression is not None
        value = self.lower_expression(expression)
        self.builder.emit(OpCode.PARAM, value.operand, location=location)
        self.builder.emit(
            OpCode.CALL,
            Operand(OperandKind.LABEL, PRINT_LABEL),
            Operand(OperandKind.CONSTANT, 1, INTEGER),
            location=location,
        )
        value.release(self.builder, location)

    # -- stores and conversions -------------------------------------------------

    def direct_destination(self, node: ParseTreeNode, symbol: Symbol) -> Operand | None:
        """The SYMBOL operand a result can be written to directly, if any."""
        return Operand(OperandKind.SYMBOL, self.facts.address_for(symbol), symbol.type)

    def store_symbol(
        self,
        node: ParseTreeNode,
        symbol: Symbol,
        value: ValueRef,
        location: SourceLocation,
    ) -> None:
        """Copy ``value`` into the storage of ``symbol``; the caller keeps ``value``."""
        destination = self.direct_destination(node, symbol)
        assert destination is not None
        self.builder.emit(OpCode.COPY, value.operand, result=destination, location=location)

    def emit_into_symbol(
        self,
        node: ParseTreeNode,
        symbol: Symbol,
        opcode: OpCode,
        arg1: Operand | None,
        arg2: Operand | None,
        location: SourceLocation,
    ) -> None:
        """Emit ``opcode`` with ``symbol`` as its result, through a temporary if needed."""
        destination = self.direct_destination(node, symbol)
        if destination is not None:
            self.builder.emit(opcode, arg1, arg2, destination, location)
            return
        value = ValueRef(self.builder.temporary(symbol.type), symbol.type, True, location)
        self.builder.emit(opcode, arg1, arg2, value.operand, location)
        self.store_symbol(node, symbol, value, location)
        value.release(self.builder, location)

    def coerce(self, value: ValueRef, target: Type, location: SourceLocation) -> ValueRef:
        """Make an implicit integer→float widening explicit; other values pass through."""
        if target != FLOAT or value.type != INTEGER:
            return value
        operand = value.operand
        if operand.kind is OperandKind.CONSTANT and type(operand.value) is int:
            return ValueRef(
                Operand(OperandKind.CONSTANT, float(operand.value), FLOAT), FLOAT,
                location=location,
            )
        result = self.builder.temporary(FLOAT)
        self.builder.emit(
            OpCode.CAST, operand, Operand(OperandKind.LABEL, "float"), result, location
        )
        value.release(self.builder, location)
        return ValueRef(result, FLOAT, True, location)

    def lower_numeric_binary(self, node: ParseTreeNode) -> ValueRef:
        """Mixed integer/float operands are widened before the typed operation."""
        left_node, right_node = self.rule_children(node)
        left_type = self.fact(left_node).type
        right_type = self.fact(right_node).type
        if {left_type, right_type} != {INTEGER, FLOAT}:
            return self.expressions.lower_default(node)
        fact = self.fact(node)
        location = fact.location or self.location(node)
        left = self.coerce(
            self.expressions.snapshot(self.lower_expression(left_node), location),
            FLOAT,
            location,
        )
        right = self.coerce(self.lower_expression(right_node), FLOAT, location)
        return self.expressions.emit_value(
            _NUMERIC_BINARY[node.alternative or ""], left, right, fact.type, location
        )

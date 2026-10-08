"""Lower typed expression tree nodes to structured TAC."""

from __future__ import annotations

from collections.abc import Iterable

from src.antlr_mode.parse_tree import ParseTreeNode
from src.codegen.builder import IRBuilder
from src.codegen.contracts import Address, CodegenError, SemanticFacts, ValueRef
from src.codegen.ir import OpCode, Operand, OperandKind
from src.semantic.diagnostics import SourceLocation
from src.semantic.symbol_table import Symbol
from src.semantic.types import INTEGER, Type
from src.semantic.values import SemanticValue


_BINARY: dict[str, OpCode] = {
    "AddExpr": OpCode.ADD, "SubExpr": OpCode.SUB,
    "MulExpr": OpCode.MUL, "DivExpr": OpCode.DIV, "ModExpr": OpCode.MOD,
    "EqualsExpr": OpCode.EQ, "NotEqualsExpr": OpCode.NE,
    "LessExpr": OpCode.LT, "LessEqualExpr": OpCode.LE,
    "GreaterExpr": OpCode.GT, "GreaterEqualExpr": OpCode.GE,
}
_UNARY = {"NegExpr": OpCode.NEG, "NotExpr": OpCode.NOT}
_LITERALS = {
    "Literal", "FloatLiteralExpr", "IntegerLiteralExpr", "StringLiteralExpr",
    "NullLiteral", "TrueLiteral", "FalseLiteral",
}
_WRAPPERS = {
    "ExprNoAssign", "ConditionalAtom", "LogicalOrAtom", "LogicalAndAtom",
    "EqualityAtom", "RelationalAtom", "AdditiveAtom", "MultiplicativeAtom",
    "UnaryAtom", "LiteralPrimary", "LeftHandSidePrimary", "ParenPrimary",
    "LeftHandSideAtom",
}


class ExpressionLowerer:
    """Consume parsed structure and semantic facts without running type checking."""

    def __init__(self, builder: IRBuilder, facts: SemanticFacts) -> None:
        self.builder = builder
        self.facts = facts

    def lower(self, node: ParseTreeNode) -> ValueRef:
        alternative = node.alternative
        children = self._rule_children(node)
        if alternative in _LITERALS:
            fact = self._fact(node)
            return ValueRef(
                Operand(OperandKind.CONSTANT, fact.constant_value, fact.type),
                fact.type,
                location=self._location(node, fact),
            )
        if alternative == "IdentifierExpr":
            fact = self._fact(node)
            symbol = self._symbol(node)
            address = self._address(symbol, node)
            if address.symbol is not symbol:
                raise CodegenError(
                    "IRGEN-ADDRESS-MISMATCH",
                    "address does not retain resolved symbol",
                    self._location(node, fact),
                )
            return ValueRef(
                Operand(OperandKind.SYMBOL, address, fact.type),
                fact.type,
                location=self._location(node, fact),
            )
        if alternative in _BINARY:
            self._expect_children(node, children, 2)
            fact = self._fact(node)
            location = self._location(node, fact)
            left = self.snapshot(self.lower(children[0]), location)
            right = self.lower(children[1])
            return self.emit_value(
                _BINARY[alternative], left, right, fact.type, location
            )
        if alternative in _UNARY:
            self._expect_children(node, children, 1)
            operand = self.lower(children[0])
            fact = self._fact(node)
            return self.emit_value(
                _UNARY[alternative], operand, None, fact.type, self._location(node, fact)
            )
        if alternative in ("AndExpr", "OrExpr"):
            self._expect_children(node, children, 2)
            return self._short_circuit(node, children[0], children[1], alternative == "AndExpr")
        if alternative == "TernaryExpr":
            self._expect_children(node, children, 3)
            return self._ternary(node, *children)
        if alternative == "AssignExpr":
            self._expect_children(node, children, 2)
            return self._assignment(node, children[0], children[1])
        if (alternative in _WRAPPERS or (
            alternative is None and node.rule_name == "expression"
        )) and len(children) == 1:
            return self.lower(children[0])
        raise CodegenError(
            "IRGEN-UNSUPPORTED-NODE",
            f"unsupported expression {alternative or node.rule_name}",
            self._location(node),
        )

    def emit_value(
        self,
        opcode: OpCode,
        arg1: ValueRef,
        arg2: ValueRef | None,
        result_type: Type,
        location: SourceLocation,
    ) -> ValueRef:
        """Emit a value operation and consume owned input temporaries."""
        result = self.builder.temporary(result_type)
        self.builder.emit(opcode, arg1.operand, arg2.operand if arg2 else None, result, location)
        arg1.release(self.builder, location)
        if arg2 is not None and arg2.operand != arg1.operand:
            arg2.release(self.builder, location)
        return ValueRef(result, result_type, True, location)

    def snapshot(self, value: ValueRef, location: SourceLocation) -> ValueRef:
        """Capture a symbol's current value before evaluating a later expression."""
        if value.operand.kind is not OperandKind.SYMBOL:
            return value
        temporary = self.builder.temporary(value.type)
        self.builder.emit(OpCode.COPY, value.operand, result=temporary, location=location)
        return ValueRef(temporary, value.type, True, location)

    def lower_arguments(self, nodes: Iterable[ParseTreeNode]) -> tuple[ValueRef, ...]:
        """Evaluate call arguments left to right and capture each value immediately."""
        values: list[ValueRef] = []
        for node in nodes:
            value = self.lower(node)
            values.append(self.snapshot(value, value.location or self._location(node)))
        return tuple(values)

    def emit_store(
        self,
        opcode: OpCode,
        base: ValueRef,
        selector: ValueRef,
        value: ValueRef,
        location: SourceLocation,
    ) -> ValueRef:
        """Emit LIST_SET, FIELD_SET, or ENV_SET; retain the stored value."""
        if opcode not in (OpCode.LIST_SET, OpCode.FIELD_SET, OpCode.ENV_SET):
            raise ValueError("emit_store requires a store opcode")
        self.builder.emit(opcode, base.operand, selector.operand, value.operand, location)
        if base.operand != value.operand:
            base.release(self.builder, location)
        if selector.operand not in (base.operand, value.operand):
            selector.release(self.builder, location)
        return value

    def emit_call(
        self,
        target: Operand,
        arguments: Iterable[ValueRef],
        return_type: Type | None,
        location: SourceLocation,
        *,
        closure: bool = False,
    ) -> ValueRef | None:
        """Emit previously captured arguments in source order and an optional result."""
        supplied = tuple(arguments)
        for argument in supplied:
            self.builder.emit(OpCode.PARAM, argument.operand, location=location)
        result = self.builder.temporary(return_type) if return_type is not None else None
        self.builder.emit(
            OpCode.CLOSURE_CALL if closure else OpCode.CALL,
            target,
            Operand(OperandKind.CONSTANT, len(supplied), INTEGER),
            result,
            location,
        )
        released: set[Operand] = set()
        for argument in supplied:
            if argument.owns_temporary and argument.operand not in released:
                argument.release(self.builder, location)
                released.add(argument.operand)
        if result is not None and return_type is not None:
            return ValueRef(result, return_type, True, location)
        return None

    def _short_circuit(
        self,
        node: ParseTreeNode,
        left_node: ParseTreeNode,
        right_node: ParseTreeNode,
        is_and: bool,
    ) -> ValueRef:
        fact = self._fact(node)
        location = self._location(node, fact)
        result_type = fact.type
        left = self.lower(left_node)
        result = self.builder.temporary(result_type)
        self.builder.emit(OpCode.COPY, left.operand, result=result, location=location)
        left.release(self.builder, location)
        end = self.builder.labels.next("logic_end")
        if is_and:
            self.builder.branch_false(result, end, location)
        else:
            self.builder.branch_true(result, end, location)
        right = self.lower(right_node)
        self.builder.emit(OpCode.COPY, right.operand, result=result, location=location)
        right.release(self.builder, location)
        self.builder.mark(end, location)
        return ValueRef(result, result_type, True, location)

    def _ternary(
        self,
        node: ParseTreeNode,
        condition_node: ParseTreeNode,
        true_node: ParseTreeNode,
        false_node: ParseTreeNode,
    ) -> ValueRef:
        fact = self._fact(node)
        location = self._location(node, fact)
        result_type = fact.type
        condition = self.lower(condition_node)
        result = self.builder.temporary(result_type)
        false_label = self.builder.labels.next("ternary_false")
        end_label = self.builder.labels.next("ternary_end")
        self.builder.branch_false(condition.operand, false_label, location)
        true_value = self.lower(true_node)
        self.builder.emit(OpCode.COPY, true_value.operand, result=result, location=location)
        true_value.release(self.builder, location)
        self.builder.jump(end_label, location)
        self.builder.mark(false_label, location)
        false_value = self.lower(false_node)
        self.builder.emit(OpCode.COPY, false_value.operand, result=result, location=location)
        false_value.release(self.builder, location)
        self.builder.mark(end_label, location)
        condition.release(self.builder, location)
        return ValueRef(result, result_type, True, location)

    def _assignment(self, node: ParseTreeNode, lhs: ParseTreeNode, rhs: ParseTreeNode) -> ValueRef:
        location = self._location(node, self._fact(node))
        symbol = self._symbol(lhs)
        address = self._address(symbol, node)
        if address.symbol is not symbol:
            raise CodegenError(
                "IRGEN-ADDRESS-MISMATCH",
                "assignment address does not retain resolved symbol",
                location,
            )
        value = self.lower(rhs)
        value = self.snapshot(value, location)
        destination = Operand(OperandKind.SYMBOL, address, symbol.type)
        self.builder.emit(OpCode.COPY, value.operand, result=destination, location=location)
        return value

    def _symbol(self, node: ParseTreeNode) -> Symbol:
        if node.alternative not in _WRAPPERS | {"IdentifierExpr"}:
            raise CodegenError(
                "IRGEN-UNSUPPORTED-NODE",
                "assignment target is not a simple identifier",
                self._location(node),
            )
        symbol = self.facts.symbol_for(node)
        if symbol is not None:
            return symbol
        for child in self._rule_children(node):
            try:
                return self._symbol(child)
            except CodegenError as error:
                if error.code != "IRGEN-MISSING-SYMBOL":
                    raise
        raise CodegenError("IRGEN-MISSING-SYMBOL", "missing resolved Symbol", self._location(node))

    def _fact(self, node: ParseTreeNode) -> SemanticValue:
        try:
            fact = self.facts.value_for(node)
        except LookupError as error:
            raise CodegenError(
                "IRGEN-MISSING-FACT", "missing SemanticValue", self._location(node)
            ) from error
        if not isinstance(fact, SemanticValue):
            raise CodegenError(
                "IRGEN-MISSING-FACT", "missing SemanticValue", self._location(node)
            )
        return fact

    def _address(self, symbol: Symbol, node: ParseTreeNode) -> Address:
        try:
            address = self.facts.address_for(symbol)
        except LookupError as error:
            raise CodegenError(
                "IRGEN-MISSING-ADDRESS", "missing symbol Address", self._location(node)
            ) from error
        if not isinstance(address, Address):
            raise CodegenError(
                "IRGEN-MISSING-ADDRESS", "missing symbol Address", self._location(node)
            )
        return address

    @staticmethod
    def _rule_children(node: ParseTreeNode) -> list[ParseTreeNode]:
        return [child for child in node.children if child.rule_name is not None]

    @staticmethod
    def _expect_children(node: ParseTreeNode, children: list[ParseTreeNode], count: int) -> None:
        if len(children) != count:
            raise CodegenError(
                "IRGEN-MALFORMED-NODE",
                f"expected {count} expression children",
                ExpressionLowerer._location(node),
            )

    @staticmethod
    def _location(node: ParseTreeNode, fact: SemanticValue | None = None) -> SourceLocation:
        if fact is not None and fact.location is not None:
            return fact.location
        if node.line is None or node.column is None:
            raise CodegenError("IRGEN-MISSING-LOCATION", "expression has no source coordinates")
        return SourceLocation(node.line, node.column, node.end_line, node.end_column)

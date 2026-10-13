"""Procedures, calls, returns, recursion and closures (block 3).

Mixed into ``CompiscriptCodeGenerator``. Every function body becomes one
``IRProcedure`` labelled from the extended symbol table; labels exist before any
body is lowered, so direct and mutual recursion are plain calls (FUN-05, FUN-06).

Hidden parameters come first (``this``, then ``env``), then the declared ones in
source order. A call emits its arguments left to right (FUN-03):

* a function that needs no environment: ``param a`` … ``t = call fn_f, n``;
* a nested function that needs one: ``c = closure fn_f.g, e`` then
  ``t = closure_call c, n``; the environment travels inside the closure;
* any other callable value (``let h = f; h()``): ``t = closure_call h, n``.

Closures capture by reference: a captured variable lives in its owner's
environment. The owner creates it in its prologue (``e = env_new size``), links
the environment it received and copies captured parameters; afterwards the owner
reads and writes those variables with ``env_get``/``env_set`` on ``e`` and inner
functions reach them through ``env`` with Nadissa's ``depth:offset`` access
(FUN-07, FUN-08). The environment pointer is a temporary that lives for the
whole activation, so it is dropped without a ``release`` marker.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from src.antlr_mode.parse_tree import ParseTreeNode
from src.codegen.activation import (
    ActivationRecordLayout,
    FrameSlot,
    enclosing_function,
    function_symbol_of,
    parent_function,
)
from src.codegen.contracts import Address, CodegenError, ValueRef
from src.codegen.ir import OpCode, Operand, OperandKind
from src.codegen.layout import StorageClass
from src.semantic.diagnostics import SourceLocation
from src.semantic.symbol_table import Scope, Symbol, SymbolKind
from src.semantic.types import INTEGER, NULL, UNKNOWN, VOID, FunctionType, Type

CALLS = frozenset({"CallExprNoArgs", "CallExprWithArgs"})


@dataclass(frozen=True, slots=True)
class ProcedureContext:
    """The activation being lowered: its frame, hidden operands and environment."""

    frame: ActivationRecordLayout
    scope: Scope | None
    return_type: Type
    hidden: Mapping[str, Operand] = field(default_factory=dict)
    environment: Operand | None = None


class CallableLowering:
    """Function procedures, calls, returns and lexical environments."""

    STATEMENTS = {
        "functionDeclaration": "lower_function_declaration",
        "returnStatement": "lower_return",
    }
    EXPRESSIONS = {
        "IdentifierExpr": "lower_identifier",
        "CallExprNoArgs": "lower_call",
        "CallExprWithArgs": "lower_call",
        "AssignExpr": "lower_assign_expression",
    }
    PROCEDURES = {"functionDeclaration": "lower_function_procedure"}

    # -- procedures --------------------------------------------------------------

    def lower_function_declaration(self, node: ParseTreeNode) -> None:
        """A declaration emits nothing in place: its body is its own procedure."""

    def lower_function_procedure(self, node: ParseTreeNode) -> None:
        function = self.declared_symbol(node)
        frame = self.frame_of(function, node)
        signature = function.type
        return_type = signature.return_type if isinstance(signature, FunctionType) else UNKNOWN
        self.lower_procedure(
            node, frame, self.facts.scope_for(node), return_type, self.child(node, "block")
        )

    def lower_procedure(
        self,
        node: ParseTreeNode,
        frame: ActivationRecordLayout,
        scope: Scope | None,
        return_type: Type,
        body: ParseTreeNode | None,
        preamble: Callable[[ProcedureContext], None] | None = None,
    ) -> None:
        """Open a procedure, run its prologue and body, close it with a final return."""
        location = self.location(node)
        hidden = {
            slot.name: self.hidden_operand(frame, slot, location)
            for slot in frame.hidden_parameters
        }
        declared = tuple(
            Operand(OperandKind.SYMBOL, self.facts.address_for(slot.symbol), slot.symbol.type)
            for slot in frame.parameters
        )
        self.builder.begin_procedure(
            Operand(OperandKind.LABEL, frame.label), (*hidden.values(), *declared)
        )
        self.reachable = True
        saved_targets = (self.break_targets, self.continue_targets)
        self.break_targets, self.continue_targets = [], []
        context = ProcedureContext(
            frame, scope, return_type, hidden, self._open_environment(frame, hidden, location)
        )
        self.function_stack.append(context)
        try:
            if preamble is not None:
                preamble(context)
            if body is not None:
                self.lower_block(body)
            if self.reachable:
                self.builder.emit(OpCode.RETURN, location=location)
                self.reachable = False
        finally:
            self.function_stack.pop()
            self.break_targets, self.continue_targets = saved_targets
        if context.environment is not None:
            self.builder.temporaries.release(context.environment)
        self.builder.end_procedure()

    def _open_environment(
        self,
        frame: ActivationRecordLayout,
        hidden: Mapping[str, Operand],
        location: SourceLocation,
    ) -> Operand | None:
        """Prologue of a function that owns captured variables or forwards a chain."""
        environment = frame.environment
        if environment is None:
            return None
        pointer = self.builder.temporary(UNKNOWN)
        self.builder.emit(
            OpCode.ENV_NEW, Operand(OperandKind.CONSTANT, environment.size, INTEGER),
            result=pointer, location=location,
        )
        if "env" in hidden:
            self.builder.emit(
                OpCode.ENV_SET, pointer, Operand(OperandKind.OFFSET, environment.parent_offset),
                hidden["env"], location,
            )
        for slot in environment.slots:
            if self.layouts.symbols.layout_for(slot.symbol).storage is StorageClass.PARAMETER:
                parameter = Operand(
                    OperandKind.SYMBOL, self.facts.address_for(slot.symbol), slot.symbol.type
                )
                self.builder.emit(
                    OpCode.ENV_SET, pointer, Operand(OperandKind.OFFSET, slot.offset),
                    parameter, location,
                )
        return pointer

    def hidden_operand(
        self, frame: ActivationRecordLayout, slot: FrameSlot, location: SourceLocation
    ) -> Operand:
        """``this``/``env`` have no semantic Symbol: they are synthesized per frame."""
        key = (frame.label, slot.name)
        if key not in self.hidden_operands:
            type_ = slot.type or UNKNOWN
            symbol = Symbol(slot.name, SymbolKind.PARAMETER, type_, False, location)
            address = Address(
                symbol, StorageClass.PARAMETER.value, slot.name, slot.offset, frame.label
            )
            self.hidden_operands[key] = Operand(OperandKind.SYMBOL, address, type_)
        return self.hidden_operands[key]

    def frame_of(self, function: Symbol, node: ParseTreeNode) -> ActivationRecordLayout:
        try:
            return self.layouts.frame_for(function)
        except LookupError as error:
            raise CodegenError(
                "IRGEN-MISSING-FRAME",
                f"no activation record for {function.name}",
                self.location(node),
            ) from error

    def lower_return(self, node: ParseTreeNode) -> None:
        location = self.location(node)
        if not self.function_stack:
            raise CodegenError(
                "IRGEN-RETURN-OUTSIDE-FUNCTION", "return outside a procedure", location
            )
        expression = self.child(node, "expression")
        if expression is None:
            self.builder.emit(OpCode.RETURN, location=location)
        else:
            value = self.coerce(
                self.lower_expression(expression), self.function_stack[-1].return_type, location
            )
            self.builder.emit(OpCode.RETURN, value.operand, location=location)
        self.reachable = False

    # -- identifiers and environments --------------------------------------------

    def lower_identifier(self, node: ParseTreeNode) -> ValueRef:
        symbol = self.facts.symbol_for(node)
        if symbol is None:
            return self.expressions.lower_default(node)
        if symbol.kind is SymbolKind.FUNCTION:
            return self.function_value(symbol, node)
        if symbol.kind is SymbolKind.CLASS:
            raise CodegenError(
                "IRGEN-UNSUPPORTED-NODE",
                f"class {symbol.name} used as a value",
                self.location(node),
            )
        cell = self.environment_cell(node, symbol)
        if cell is None:
            return self.expressions.lower_default(node)
        location = self.location(node)
        result = self.builder.temporary(symbol.type)
        self.builder.emit(OpCode.ENV_GET, cell[0], cell[1], result, location)
        return ValueRef(result, symbol.type, True, location)

    def environment_cell(
        self, node: ParseTreeNode, symbol: Symbol
    ) -> tuple[Operand, Operand] | None:
        """``(environment, offset)`` of a captured variable as seen from ``node``."""
        if symbol not in self.layouts.symbols:
            return None
        layout = self.layouts.symbols.layout_for(symbol)
        if not layout.captured or not self.function_stack:
            return None
        context = self.function_stack[-1]
        try:
            access = self.facts.lexical_access(node, symbol)
        except LookupError as error:
            raise CodegenError(
                "IRGEN-MISSING-FACT", f"no lexical access for {symbol.name}", self.location(node)
            ) from error
        if access.kind == "captured":
            if "env" not in context.hidden:
                raise CodegenError(
                    "IRGEN-ENV-UNAVAILABLE",
                    f"{context.frame.label} receives no environment for {symbol.name}",
                    self.location(node),
                )
            assert access.offset is not None
            offset = Operand(OperandKind.OFFSET, (access.depth, access.offset))
            return context.hidden["env"], offset
        if access.kind == "local" and context.environment is not None:
            assert layout.env_offset is not None
            return context.environment, Operand(OperandKind.OFFSET, layout.env_offset)
        return None

    def direct_destination(self, node: ParseTreeNode, symbol: Symbol) -> Operand | None:
        if self.environment_cell(node, symbol) is not None:
            return None
        return super().direct_destination(node, symbol)

    def store_symbol(
        self,
        node: ParseTreeNode,
        symbol: Symbol,
        value: ValueRef,
        location: SourceLocation,
    ) -> None:
        cell = self.environment_cell(node, symbol)
        if cell is None:
            super().store_symbol(node, symbol, value, location)
            return
        self.builder.emit(OpCode.ENV_SET, cell[0], cell[1], value.operand, location)

    def environment_pointer(
        self, function: Symbol, location: SourceLocation
    ) -> tuple[Operand, ValueRef | None]:
        """The environment a nested ``function`` must be closed over, from here.

        It is the environment created by the function that declares it: our own
        ``e`` when we are that function, otherwise ``env`` followed up the access
        links. The second item is a temporary the caller must release.
        """
        creator = enclosing_function(self.facts.declaring_scope(function))
        if creator is None:
            return Operand(OperandKind.CONSTANT, None, NULL), None
        context = self.function_stack[-1] if self.function_stack else None
        if context is not None and context.scope is creator and context.environment is not None:
            return context.environment, None
        unavailable = CodegenError(
            "IRGEN-ENV-UNAVAILABLE",
            f"no environment of {creator.name} is reachable to close over {function.name}",
            location,
        )
        if context is None or context.scope is None or "env" not in context.hidden:
            raise unavailable
        pointer: Operand = context.hidden["env"]
        owned: ValueRef | None = None
        walker = parent_function(context.scope)
        while walker is not creator:
            owner = function_symbol_of(walker) if walker is not None else None
            frame = self.layouts.frame_for(owner) if owner is not None else None
            if frame is None or frame.environment is None or not frame.needs_env:
                raise unavailable
            link = self.builder.temporary(UNKNOWN)
            self.builder.emit(
                OpCode.ENV_GET,
                pointer,
                Operand(OperandKind.OFFSET, frame.environment.parent_offset),
                link,
                location,
            )
            if owned is not None:
                owned.release(self.builder, location)
            owned = ValueRef(link, UNKNOWN, True, location)
            pointer = link
            walker = parent_function(walker)
        return pointer, owned

    def function_value(self, function: Symbol, node: ParseTreeNode) -> ValueRef:
        """A function used as a value is a closure of its label and environment."""
        location = self.location(node)
        frame = self.frame_of(function, node)
        if frame.needs_env:
            pointer, owned = self.environment_pointer(function, location)
        else:
            pointer, owned = Operand(OperandKind.CONSTANT, None, NULL), None
        result = self.builder.temporary(function.type)
        self.builder.emit(
            OpCode.CLOSURE, Operand(OperandKind.LABEL, frame.label), pointer, result, location
        )
        if owned is not None:
            owned.release(self.builder, location)
        return ValueRef(result, function.type, True, location)

    def lower_assign_expression(self, node: ParseTreeNode) -> ValueRef:
        """``x = e`` as an expression returns the stored value (also for captures)."""
        target_node, value_node = self.rule_children(node)
        target = self.unwrap(target_node)
        if target.alternative != "IdentifierExpr":
            return self.expressions.lower_default(node)
        symbol = self.facts.symbol_for(target)
        if symbol is None:
            return self.expressions.lower_default(node)
        location = self.location(node)
        value = self.expressions.snapshot(
            self.coerce(self.lower_expression(value_node), symbol.type, location), location
        )
        self.store_symbol(node, symbol, value, location)
        return value

    # -- calls -------------------------------------------------------------------

    def lower_expression_statement(self, node: ParseTreeNode) -> None:
        """A call used as a statement discards its result instead of naming it."""
        expression = self.child(node, "expression")
        assert expression is not None
        core = self.unwrap(expression)
        if core.alternative in CALLS:
            self.emit_call_node(core, discard=True)
            return
        super().lower_expression_statement(node)

    def lower_call(self, node: ParseTreeNode) -> ValueRef:
        value = self.emit_call_node(node, discard=False)
        if value is None:
            raise CodegenError(
                "IRGEN-VOID-VALUE", "a void call has no value to use", self.location(node)
            )
        return value

    def emit_call_node(self, node: ParseTreeNode, *, discard: bool) -> ValueRef | None:
        location = self.location(node)
        callee_node = self.rule_children(node)[0]
        callee = self.unwrap(callee_node)
        return_type = self.fact(node).type
        result_type = None if discard or return_type == VOID else return_type
        arguments = self.call_arguments(node)
        method = self.method_call(node, callee, arguments, result_type, location)
        if method is not NotImplemented:
            return method
        symbol = self.facts.symbol_for(callee) if callee.alternative == "IdentifierExpr" else None
        if symbol is not None and symbol.kind is SymbolKind.FUNCTION:
            frame = self.frame_of(symbol, node)
            if not frame.needs_env:
                values = self.lower_call_arguments(arguments, symbol.type)
                return self.invoke(
                    OpCode.CALL, Operand(OperandKind.LABEL, frame.label),
                    values, values, result_type, location,
                )
            closure = self.function_value(symbol, callee)
        else:
            closure = self.lower_expression(callee_node)
            if any(self.may_write(argument) for argument in arguments):
                closure = self.expressions.snapshot(closure, location)
        values = self.lower_call_arguments(arguments, closure.type)
        return self.invoke(
            OpCode.CLOSURE_CALL, closure.operand, values, (*values, closure), result_type, location
        )

    def method_call(
        self,
        node: ParseTreeNode,
        callee: ParseTreeNode,
        arguments: list[ParseTreeNode],
        result_type: Type | None,
        location: SourceLocation,
    ) -> ValueRef | None:
        """Hook for method invocation; ``NotImplemented`` when ``callee`` is no method."""
        return NotImplemented

    def call_arguments(self, node: ParseTreeNode) -> list[ParseTreeNode]:
        """Argument expressions in source order."""
        return self.list_items(node, "argumentList")

    def lower_call_arguments(
        self, arguments: list[ParseTreeNode], signature: Type
    ) -> tuple[ValueRef, ...]:
        """Evaluate left to right, then widen to the declared parameter types."""
        values = self.expressions.lower_arguments(arguments)
        if not isinstance(signature, FunctionType):
            return values
        return tuple(
            self.coerce(value, expected, value.location or self.location(argument))
            for value, expected, argument in zip(values, signature.parameter_types, arguments)
        ) + values[len(signature.parameter_types):]

    def invoke(
        self,
        opcode: OpCode,
        target: Operand,
        parameters: tuple[ValueRef, ...],
        consumed: tuple[ValueRef, ...],
        result_type: Type | None,
        location: SourceLocation,
    ) -> ValueRef | None:
        """``param``… then the call; owned inputs are released after it."""
        for parameter in parameters:
            self.builder.emit(OpCode.PARAM, parameter.operand, location=location)
        result = self.builder.temporary(result_type) if result_type is not None else None
        self.builder.emit(
            opcode,
            target,
            Operand(OperandKind.CONSTANT, len(parameters), INTEGER),
            result,
            location,
        )
        released: set[Operand] = set()
        for value in consumed:
            if value.owns_temporary and value.operand not in released:
                value.release(self.builder, location)
                released.add(value.operand)
        if result is None or result_type is None:
            return None
        return ValueRef(result, result_type, True, location)

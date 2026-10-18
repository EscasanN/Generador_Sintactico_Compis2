"""Classes, objects, methods, ``this`` and lists (block 3).

Mixed into ``CompiscriptCodeGenerator``. Instances follow Nadissa's
``ClassLayout``: inherited fields first, methods outside the instance.

* ``new C(a)``: ``t = object_new C, size``, ``param t``, ``param a``,
  ``call C.constructor, n+1`` (CLS-02). A class without an explicit
  constructor gets a synthesized ``C.constructor(this)`` procedure (CLS-05).
* Every constructor starts by running the field initializers of the class and
  its bases, base first, as ``field_set this, offset, value``: the grammar has
  no ``super`` and semantics never runs a base constructor.
* Fields are read and written by offset (``field_get``/``field_set``, CLS-03).
  Methods receive the receiver as their first, hidden parameter (CLS-04) and are
  resolved statically by (class, name) through the class layout, because
  semantics may record a member before its final declaration.
* Lists: ``list_new n`` then ``list_set`` per element in order, ``list_get``
  for reads and ``list_set`` for indexed stores; indexes are logical (LST-*).

A receiver or list operand is first copied to a temporary only when a later
operand of the same operation may change it (an assignment, call or ``new``).
"""

from __future__ import annotations

from src.antlr_mode.parse_tree import ParseTreeNode
from src.codegen.activation import parent_function
from src.codegen.callables import ProcedureContext
from src.codegen.contracts import CodegenError, ValueRef
from src.codegen.ir import OpCode, Operand, OperandKind
from src.codegen.layout import ClassLayout
from src.semantic.diagnostics import SourceLocation
from src.semantic.symbol_table import Symbol, SymbolKind
from src.semantic.types import INTEGER, UNKNOWN, VOID, ArrayType, ClassType, FunctionType, Type

_LITERAL_LISTS = frozenset({"EmptyArrayLiteral", "NonEmptyArrayLiteral"})


class ObjectLowering:
    """Object creation, constructors, members, ``this`` and list operations."""

    STATEMENTS = {
        "classDeclaration": "lower_class_declaration",
        "PropertyAssignment": "lower_property_assignment",
    }
    EXPRESSIONS = {
        "ThisExpr": "lower_this",
        "NewExprNoArgs": "lower_new",
        "NewExprWithArgs": "lower_new",
        "PropertyAccessExpr": "lower_property_access",
        "PropertyAssignExpr": "lower_property_assign_expression",
        "IndexExpr": "lower_index",
        "ArrayLiteralExpr": "lower_array_literal",
        "EmptyArrayLiteral": "lower_array_literal",
        "NonEmptyArrayLiteral": "lower_array_literal",
    }
    PROCEDURES = {"classDeclaration": "lower_class_procedures"}

    # -- class procedures --------------------------------------------------------

    def lower_class_declaration(self, node: ParseTreeNode) -> None:
        """A class declaration emits nothing in place; its code is in procedures."""

    def lower_class_procedures(self, node: ParseTreeNode) -> None:
        """Constructor (explicit or synthesized) and every method, in source order."""
        layout = self.class_layout_of(self.declared_symbol(node), node)
        methods = [
            member
            for holder in self.children(node, "classMember")
            for member in self.rule_children(holder)
            if member.rule_name == "classMethod"
        ]
        self.class_stack.append(layout)
        try:
            if not layout.explicit_constructor:
                self._lower_implicit_constructor(node, layout)
            for method in methods:
                self._lower_method(method, layout)
        finally:
            self.class_stack.pop()

    def _lower_method(self, node: ParseTreeNode, layout: ClassLayout) -> None:
        name = self.identifier(node)
        frame = self.layouts.frame_by_label(layout.method_label(name))
        signature = frame.function.type if frame.function is not None else UNKNOWN
        return_type = signature.return_type if isinstance(signature, FunctionType) else UNKNOWN
        location = self.location(node)

        def initialize(context: ProcedureContext) -> None:
            self._initialize_fields(layout, context, location)

        self.lower_procedure(
            node, frame, self.facts.scope_for(node), return_type,
            self.child(node, "block"), initialize if name == "constructor" else None,
            bound_environment_offset=layout.environment_offset if frame.needs_env else None,
        )

    def _lower_implicit_constructor(self, node: ParseTreeNode, layout: ClassLayout) -> None:
        """``C.constructor(this)``: field initializers only (CLS-05)."""
        frame = self.layouts.frame_by_label(layout.constructor_label)
        scope = self.layouts.captures.constructor_scopes[id(layout.symbol)]
        location = self.location(node)
        self.lower_procedure(
            node, frame, scope, VOID, None,
            lambda context: self._initialize_fields(layout, context, location),
            bound_environment_offset=layout.environment_offset if frame.needs_env else None,
        )

    def _initialize_fields(
        self, layout: ClassLayout, context: ProcedureContext, location: SourceLocation
    ) -> None:
        """``field_set this, offset, value`` for every initialized field, base first."""
        chain: list[ClassLayout] = []
        current: ClassLayout | None = layout
        while current is not None:
            chain.insert(0, current)
            current = current.superclass
        this = context.hidden["this"]
        for owner in chain:
            saved_owner = self.initializer_owner
            saved_context = self.function_stack[-1]
            environment: ValueRef | None = None
            self.initializer_owner = owner
            try:
                if owner is not layout:
                    # Base initializers execute here, but their captures refer
                    # to the base's defining environment, not the child's.
                    hidden = {"this": this}
                    if owner.environment_offset is not None:
                        operand = self.builder.temporary(UNKNOWN)
                        self.builder.emit(
                            OpCode.FIELD_GET, this,
                            Operand(OperandKind.OFFSET, owner.environment_offset),
                            operand, location,
                        )
                        environment = ValueRef(operand, UNKNOWN, True, location)
                        hidden["env"] = operand
                    self.function_stack[-1] = ProcedureContext(
                        context.frame,
                        self.layouts.captures.constructor_scopes[id(owner.symbol)],
                        context.return_type,
                        hidden,
                    )
                for field, expression in self._field_initializers(owner):
                    field_location = self.location(field)
                    symbol = self.declared_symbol(field)
                    value = self.coerce(self.lower_expression(expression), symbol.type, field_location)
                    offset = self.layouts.symbols.layout_for(symbol).offset
                    self.builder.emit(
                        OpCode.FIELD_SET, this, Operand(OperandKind.OFFSET, offset),
                        value.operand, field_location,
                    )
                    value.release(self.builder, field_location)
            finally:
                self.initializer_owner = saved_owner
                self.function_stack[-1] = saved_context
                if environment is not None:
                    environment.release(self.builder, location)

    def _field_initializers(
        self, layout: ClassLayout
    ) -> list[tuple[ParseTreeNode, ParseTreeNode]]:
        """``(field, initializer expression)`` pairs declared by one class."""
        declaration = self.class_declarations().get(id(layout.symbol))
        pairs = []
        for holder in self.children(declaration, "classMember") if declaration else ():
            for field in self.rule_children(holder):
                if field.rule_name in ("classField", "classConstant"):
                    initializer = self.child(field, "initializer")
                    expression = self.child(initializer or field, "expression")
                    if expression is not None:
                        pairs.append((field, expression))
        return pairs

    def class_declarations(self) -> dict[int, ParseTreeNode]:
        """classDeclaration nodes by the identity of their class Symbol."""
        if self._class_declarations is None:
            self._class_declarations = {
                id(symbol): node
                for node in self.walk(self.root)
                if node.rule_name == "classDeclaration"
                and (symbol := self.facts.symbol_for(node)) is not None
            }
        return self._class_declarations

    # -- this, new and members ---------------------------------------------------

    def this_value(self, node: ParseTreeNode) -> ValueRef:
        context = self.function_stack[-1] if self.function_stack else None
        if context is not None:
            binding = self.layouts.captures.receiver_bindings.get(id(node))
            if binding is not None:
                cell = self.environment_cell(node, binding)
                if cell is not None and context.scope is not self.layouts.captures.owner_scope[id(binding)]:
                    location = self.location(node)
                    result = self.builder.temporary(binding.type)
                    self.builder.emit(OpCode.ENV_GET, cell[0], cell[1], result, location)
                    return ValueRef(result, binding.type, True, location)
            if "this" in context.hidden:
                operand = context.hidden["this"]
                type_ = self.initializer_owner.symbol.type if self.initializer_owner else operand.type
                return ValueRef(operand, type_, location=self.location(node))
            method = context.scope
            while method is not None:
                receiver = self.layouts.captures.receivers.get(id(method))
                if receiver is not None:
                    cell = self.environment_cell(node, receiver)
                    if cell is not None:
                        location = self.location(node)
                        result = self.builder.temporary(receiver.type)
                        self.builder.emit(OpCode.ENV_GET, cell[0], cell[1], result, location)
                        return ValueRef(result, receiver.type, True, location)
                method = parent_function(method)
        raise CodegenError(
            "IRGEN-THIS-UNAVAILABLE", "this has no lexical method receiver", self.location(node)
        )

    def lower_this(self, node: ParseTreeNode) -> ValueRef:
        return self.this_value(node)

    def lower_new(self, node: ParseTreeNode) -> ValueRef:
        """Reserve the instance, then call its constructor with ``this`` first."""
        location = self.location(node)
        class_type = self.fact(node).type
        layout = self.class_layout_of(class_type, node)
        instance = ValueRef(self.builder.temporary(class_type), class_type, True, location)
        self.builder.emit(
            OpCode.OBJECT_NEW,
            Operand(OperandKind.LABEL, layout.label),
            Operand(OperandKind.CONSTANT, layout.size, INTEGER),
            instance.operand,
            location,
        )
        for owner, offset in layout.environment_bindings:
            environment, owned = self.environment_pointer(owner.symbol, location)
            self.builder.emit(
                OpCode.FIELD_SET, instance.operand, Operand(OperandKind.OFFSET, offset),
                environment, location,
            )
            if owned is not None:
                owned.release(self.builder, location)
        members = layout.symbol.metadata.get("members", {})
        constructor = members.get("constructor") if layout.explicit_constructor else None
        signature = constructor.type if constructor is not None else UNKNOWN
        values = self.lower_call_arguments(self.call_arguments(node), signature)
        environment = self.method_environment(layout, layout.constructor_label, instance, location)
        hidden = (instance, environment) if environment is not None else (instance,)
        self.invoke(
            OpCode.CALL, Operand(OperandKind.LABEL, layout.constructor_label),
            (*hidden, *values), (*values, *((environment,) if environment else ())), None, location,
        )
        return instance

    def lower_property_access(self, node: ParseTreeNode) -> ValueRef:
        """``o.campo`` reads by offset; ``o.metodo`` used as a value is a method_ref."""
        location = self.location(node)
        (receiver_node,) = self.rule_children(node)
        name = self.identifier(node)
        receiver_type = self.fact(receiver_node).type
        receiver = self.lower_expression(receiver_node)
        member = self.facts.symbol_for(node)
        if member is not None and member.kind is SymbolKind.METHOD:
            return self._method_reference(receiver, receiver_type, name, node, location)
        field_type = self.fact(node).type
        result = self.builder.temporary(field_type)
        offset = self.member_offset_of(receiver_type, name, node)
        self.builder.emit(OpCode.FIELD_GET, receiver.operand, offset, result, location)
        receiver.release(self.builder, location)
        return ValueRef(result, field_type, True, location)

    def _method_reference(
        self,
        receiver: ValueRef,
        receiver_type: Type,
        name: str,
        node: ParseTreeNode,
        location: SourceLocation,
    ) -> ValueRef:
        type_ = self.fact(node).type
        result = self.builder.temporary(type_)
        label = self.method_label_of(receiver_type, name, node)
        self.builder.emit(OpCode.METHOD_REF, receiver.operand, label, result, location)
        receiver.release(self.builder, location)
        return ValueRef(result, type_, True, location)

    def lower_identifier(self, node: ParseTreeNode) -> ValueRef:
        """Bare member names inside a class body mean ``this.member``."""
        symbol = self.facts.symbol_for(node)
        if symbol is None or symbol.kind not in (SymbolKind.FIELD, SymbolKind.METHOD):
            return super().lower_identifier(node)
        location = self.location(node)
        this = self.this_value(node)
        if symbol.kind is SymbolKind.METHOD:
            return self._method_reference(this, this.type, symbol.name, node, location)
        result = self.builder.temporary(symbol.type)
        offset = self.member_offset_of(this.type, symbol.name, node)
        self.builder.emit(OpCode.FIELD_GET, this.operand, offset, result, location)
        this.release(self.builder, location)
        return ValueRef(result, symbol.type, True, location)

    def direct_destination(self, node: ParseTreeNode, symbol: Symbol) -> Operand | None:
        if symbol.kind is SymbolKind.FIELD:
            return None
        return super().direct_destination(node, symbol)

    def store_symbol(
        self,
        node: ParseTreeNode,
        symbol: Symbol,
        value: ValueRef,
        location: SourceLocation,
    ) -> None:
        """A bare field name as a target writes ``this`` by offset."""
        if symbol.kind is not SymbolKind.FIELD:
            super().store_symbol(node, symbol, value, location)
            return
        this = self.this_value(node)
        offset = self.member_offset_of(this.type, symbol.name, node)
        self.builder.emit(OpCode.FIELD_SET, this.operand, offset, value.operand, location)
        this.release(self.builder, location)

    def method_call(
        self,
        node: ParseTreeNode,
        callee: ParseTreeNode,
        arguments: list[ParseTreeNode],
        result_type: Type | None,
        location: SourceLocation,
    ) -> ValueRef | None:
        """``o.m(a)``: ``param o``, ``param a``, ``call Clase.m, n+1``."""
        method = self.facts.symbol_for(callee)
        if method is None or method.kind is not SymbolKind.METHOD:
            return NotImplemented
        if callee.alternative == "PropertyAccessExpr":
            (receiver_node,) = self.rule_children(callee)
            receiver_type = self.fact(receiver_node).type
            receiver = self.lower_expression(receiver_node)
            if any(self.may_write(argument) for argument in arguments):
                receiver = self.expressions.snapshot(receiver, location)
        elif callee.alternative == "IdentifierExpr":
            receiver = self.this_value(callee)
            receiver_type = receiver.type
        else:
            return NotImplemented
        label = self.method_label_of(receiver_type, method.name, callee)
        layout = self.class_layout_of(receiver_type, callee)
        environment = self.method_environment(layout, str(label.value), receiver, location)
        values = self.lower_call_arguments(arguments, method.type)
        hidden = (receiver, environment) if environment is not None else (receiver,)
        return self.invoke(
            OpCode.CALL, label, (*hidden, *values), (*hidden, *values), result_type, location
        )

    def method_environment(
        self, layout: ClassLayout, label: str, receiver: ValueRef, location: SourceLocation
    ) -> ValueRef | None:
        """Load the defining environment retained by this method's instance."""
        if not self.layouts.frame_by_label(label).needs_env:
            return None
        owner = layout
        while owner is not None:
            if label == owner.constructor_label or label in owner.methods.values():
                break
            owner = owner.superclass
        if owner is None or owner.environment_offset is None:
            raise CodegenError("IRGEN-ENV-UNAVAILABLE", f"no instance environment for {label}", location)
        result = self.builder.temporary(UNKNOWN)
        self.builder.emit(
            OpCode.FIELD_GET, receiver.operand, Operand(OperandKind.OFFSET, owner.environment_offset),
            result, location,
        )
        return ValueRef(result, UNKNOWN, True, location)

    # -- member stores -----------------------------------------------------------

    def lower_property_assignment(self, node: ParseTreeNode) -> None:
        """Statement ``o.campo = e;`` (semantics records no member Symbol here)."""
        location = self.location(node)
        receiver_node, value_node = self.children(node, "expression")
        value = self.assign_field(
            receiver_node, self.identifier(node), value_node, self.fact(node).type, location
        )
        value.release(self.builder, location)

    def lower_property_assign_expression(self, node: ParseTreeNode) -> ValueRef:
        receiver_node, value_node = self.rule_children(node)
        return self.assign_field(
            receiver_node, self.identifier(node), value_node,
            self.fact(value_node).type, self.location(node),
        )

    def lower_assign_expression(self, node: ParseTreeNode) -> ValueRef:
        """``a[i] = v`` and ``o.campo = v`` use their specialized stores (EXP-08)."""
        target_node, value_node = self.rule_children(node)
        target = self.unwrap(target_node)
        location = self.location(node)
        if target.alternative == "PropertyAccessExpr":
            (receiver_node,) = self.rule_children(target)
            return self.assign_field(
                receiver_node, self.identifier(target), value_node,
                self.fact(target).type, location,
            )
        if target.alternative == "IndexExpr":
            return self._assign_index(target, value_node, location)
        return super().lower_assign_expression(node)

    def assign_field(
        self,
        receiver_node: ParseTreeNode,
        name: str,
        value_node: ParseTreeNode,
        field_type: Type,
        location: SourceLocation,
    ) -> ValueRef:
        receiver_type = self.fact(receiver_node).type
        receiver = self.lower_expression(receiver_node)
        if self.may_write(value_node):
            receiver = self.expressions.snapshot(receiver, location)
        value = self.coerce(self.lower_expression(value_node), field_type, location)
        offset = ValueRef(self.member_offset_of(receiver_type, name, receiver_node), INTEGER)
        return self.expressions.emit_store(OpCode.FIELD_SET, receiver, offset, value, location)

    # -- lists -------------------------------------------------------------------

    def lower_array_literal(self, node: ParseTreeNode) -> ValueRef:
        """``list_new n`` and one ``list_set`` per element, left to right (LST-01)."""
        if node.alternative not in _LITERAL_LISTS:
            (literal,) = self.rule_children(node)
            return self.lower_expression(literal)
        location = self.location(node)
        list_type = self.fact(node).type
        element_type = list_type.element_type if isinstance(list_type, ArrayType) else UNKNOWN
        elements = self.list_items(node, "elementList")
        result = self.builder.temporary(list_type)
        self.builder.emit(
            OpCode.LIST_NEW, Operand(OperandKind.CONSTANT, len(elements), INTEGER),
            result=result, location=location,
        )
        for position, element in enumerate(elements):
            value = self.coerce(self.lower_expression(element), element_type, location)
            self.builder.emit(
                OpCode.LIST_SET, result, Operand(OperandKind.CONSTANT, position, INTEGER),
                value.operand, location,
            )
            value.release(self.builder, location)
        return ValueRef(result, list_type, True, location)

    def lower_index(self, node: ParseTreeNode) -> ValueRef:
        """``a[i]`` loads one element with a logical index (LST-02)."""
        location = self.location(node)
        base_node, index_node = self.rule_children(node)
        base = self.lower_expression(base_node)
        if self.may_write(index_node):
            base = self.expressions.snapshot(base, location)
        index = self.lower_expression(index_node)
        return self.expressions.emit_value(
            OpCode.LIST_GET, base, index, self.fact(node).type, location
        )

    def _assign_index(
        self, target: ParseTreeNode, value_node: ParseTreeNode, location: SourceLocation
    ) -> ValueRef:
        """``a[i] = v`` stores through ``list_set`` (LST-03)."""
        base_node, index_node = self.rule_children(target)
        base = self.lower_expression(base_node)
        if self.may_write(index_node) or self.may_write(value_node):
            base = self.expressions.snapshot(base, location)
        index = self.lower_expression(index_node)
        if self.may_write(value_node):
            index = self.expressions.snapshot(index, location)
        value = self.coerce(self.lower_expression(value_node), self.fact(target).type, location)
        return self.expressions.emit_store(OpCode.LIST_SET, base, index, value, location)

    # -- layout lookups ----------------------------------------------------------

    def class_layout_of(self, owner: Symbol | Type, node: ParseTreeNode) -> ClassLayout:
        try:
            if isinstance(owner, Symbol) or isinstance(owner, ClassType):
                return self.layouts.class_layout(owner)
        except LookupError as error:
            raise CodegenError(
                "IRGEN-MISSING-LAYOUT", f"no layout for class {owner}", self.location(node)
            ) from error
        raise CodegenError(
            "IRGEN-MISSING-LAYOUT", f"{owner} is not a class type", self.location(node)
        )

    def member_offset_of(self, owner: Type, name: str, node: ParseTreeNode) -> Operand:
        try:
            return Operand(OperandKind.OFFSET, self.facts.member_offset(owner, name))
        except LookupError as error:
            raise CodegenError(
                "IRGEN-MISSING-LAYOUT", f"no field {name} in {owner}", self.location(node)
            ) from error

    def method_label_of(self, owner: Type, name: str, node: ParseTreeNode) -> Operand:
        try:
            label = self.class_layout_of(owner, node).method_label(name)
        except LookupError as error:
            raise CodegenError(
                "IRGEN-MISSING-LAYOUT", f"no method {name} in {owner}", self.location(node)
            ) from error
        return Operand(OperandKind.LABEL, label)

"""Grammar-neutral adapters that compose the stable semantic actions.

These handlers cover values that cannot be expressed by the profile selector
language alone, such as recursively accumulated comma lists.  Every grammar
identifier is supplied by the profile; this module contains no Compiscript
rule or token names.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Iterable

from src.semantic.action_registry import ActionRegistry
from src.semantic.actions.callables import declare_function
from src.semantic.actions.classes import access_member, declare_class, declare_method
from src.semantic.actions.control_flow import validate_sequence
from src.semantic.actions.declarations import resolve_identifier
from src.semantic.symbol_table import Symbol, SymbolKind
from src.semantic.types import ERROR, UNKNOWN, VOID, FunctionType, Type
from src.semantic.values import SemanticValue

if TYPE_CHECKING:
    from src.parser.parse_tree import ParseTreeNode
    from src.semantic.evaluator import SemanticContext


def _start_list(
    context: SemanticContext,
    node: ParseTreeNode,
    first: object = None,
) -> tuple[object, ...]:
    del context, node
    return (first,)


def _append_list(
    context: SemanticContext,
    node: ParseTreeNode,
    previous: Iterable[object] = (),
    next: object = None,
) -> tuple[object, ...]:
    del context, node
    return tuple(previous) + (next,)


def _concatenated_text(node: object) -> str:
    text = getattr(node, "text", None)
    if text is not None:
        return str(text)
    children = getattr(node, "children", ())
    return "".join(_concatenated_text(child) for child in children)


def _node_text(
    context: SemanticContext,
    node: ParseTreeNode,
) -> str:
    del context
    return _concatenated_text(node)


def _build_array(
    context: SemanticContext,
    node: ParseTreeNode,
    elements: Iterable[SemanticValue] = (),
) -> SemanticValue:
    return context.expressions.array_literal(
        tuple(elements), context.location_of(node)
    )


def _assign_to_identifier(
    context: SemanticContext,
    node: ParseTreeNode,
    name: object,
    value: SemanticValue,
) -> SemanticValue:
    target = resolve_identifier(context, node, name)
    return context.expressions.assignment(
        target, value, context.location_of(node)
    )


def _assign_to_member(
    context: SemanticContext,
    node: ParseTreeNode,
    instance: SemanticValue,
    name: object,
    value: SemanticValue,
) -> SemanticValue:
    target = access_member(context, node, instance, name)
    return context.expressions.assignment(
        target, value, context.location_of(node)
    )


def _find_child_by_rule(node: object, rule_name: str) -> object | None:
    for child in getattr(node, "children", ()):
        if getattr(child, "rule_name", None) == rule_name:
            return child
    return None


def _find_child_by_token(node: object, token_type: str) -> object | None:
    for child in getattr(node, "children", ()):
        if getattr(child, "token_type", None) == token_type:
            return child
    return None


def _children_by_token(node: object, token_type: str) -> tuple[object, ...]:
    return tuple(
        child
        for child in getattr(node, "children", ())
        if getattr(child, "token_type", None) == token_type
    )


def _parameter_pair(
    parameter_node: object,
    identifier_token: str,
    type_rule: str,
) -> tuple[str, str | None]:
    identifier = _find_child_by_token(parameter_node, identifier_token)
    name = str(getattr(identifier, "text", ""))
    type_node = _find_child_by_rule(parameter_node, type_rule)
    type_text = _concatenated_text(type_node) if type_node is not None else None
    return (name, type_text)


def _collect_parameter_pairs(
    parameters_node: object | None,
    recursive_alternative: str,
    identifier_token: str,
    type_rule: str,
) -> tuple[tuple[str, str | None], ...]:
    if parameters_node is None:
        return ()
    children = tuple(getattr(parameters_node, "children", ()))
    if getattr(parameters_node, "alternative", None) == recursive_alternative:
        previous = _collect_parameter_pairs(
            children[0],
            recursive_alternative,
            identifier_token,
            type_rule,
        )
        return previous + (
            _parameter_pair(children[2], identifier_token, type_rule),
        )
    return (_parameter_pair(children[0], identifier_token, type_rule),)


def _signature_from_tree(
    node: ParseTreeNode,
    parameters_rule: str,
    recursive_parameters_alternative: str,
    identifier_token: str,
    type_rule: str,
) -> tuple[tuple[str, ...], tuple[str | None, ...], Type | str]:
    parameters_node = _find_child_by_rule(node, parameters_rule)
    type_node = _find_child_by_rule(node, type_rule)
    pairs = _collect_parameter_pairs(
        parameters_node,
        recursive_parameters_alternative,
        identifier_token,
        type_rule,
    )
    names = tuple(pair[0] for pair in pairs)
    types = tuple(pair[1] for pair in pairs)
    return_type = _concatenated_text(type_node) if type_node is not None else VOID
    return names, types, return_type


def _declare_function_from_tree(
    context: SemanticContext,
    node: ParseTreeNode,
    name: object,
    parameters_rule: str = "",
    recursive_parameters_alternative: str = "",
    identifier_token: str = "",
    type_rule: str = "",
) -> SemanticValue:
    if id(node) in context.predeclared_symbols:
        predeclared = context.predeclared_symbols[id(node)]
        if predeclared is None:
            return SemanticValue(ERROR, location=context.location_of(node))
        return SemanticValue(
            predeclared.type,
            symbol=predeclared,
            location=context.location_of(node),
        )
    names, types, return_type = _signature_from_tree(
        node,
        parameters_rule,
        recursive_parameters_alternative,
        identifier_token,
        type_rule,
    )
    return declare_function(context, node, name, types, return_type, names)


def _direct_declarations(
    node: ParseTreeNode,
    declaration_rules: set[str],
) -> tuple[ParseTreeNode, ...]:
    declarations: list[ParseTreeNode] = []
    for child in node.children:
        if child.rule_name in declaration_rules:
            declarations.append(child)
            continue
        declaration = _find_member_declaration(child, declaration_rules)
        if declaration is not None:
            declarations.append(declaration)
    return tuple(declarations)


def _predeclare_program(
    context: SemanticContext,
    node: ParseTreeNode,
    function_rule: str,
    class_rule: str,
    identifier_token: str,
    parameters_rule: str,
    recursive_parameters_alternative: str,
    type_rule: str,
    member_rule: str,
    field_rule: str,
    constant_rule: str,
    method_rule: str,
) -> None:
    """Register top-level classes and function signatures before traversal."""
    declarations = _direct_declarations(node, {function_rule, class_rule})
    class_declarations = tuple(
        item for item in declarations if item.rule_name == class_rule
    )
    function_declarations = tuple(
        item for item in declarations if item.rule_name == function_rule
    )

    pending_classes = list(class_declarations)
    declared_names = {
        context.text_of(identifiers[0])
        for declaration in class_declarations
        if (identifiers := _children_by_token(declaration, identifier_token))
    }
    while pending_classes:
        remaining: list[ParseTreeNode] = []
        progress = False
        for declaration in pending_classes:
            identifiers = _children_by_token(declaration, identifier_token)
            if not identifiers:
                continue
            superclass = identifiers[1] if len(identifiers) > 1 else None
            if superclass is not None:
                superclass_name = context.text_of(superclass)
                if (
                    superclass_name in declared_names
                    and superclass_name not in context.classes
                ):
                    remaining.append(declaration)
                    continue
            value = declare_class(
                context,
                declaration,
                identifiers[0],
                superclass,
            )
            context.predeclared_symbols[id(declaration)] = (
                value.symbol if isinstance(value.symbol, Symbol) else None
            )
            progress = True
        if not remaining:
            break
        if not progress:
            for declaration in remaining:
                identifiers = _children_by_token(declaration, identifier_token)
                superclass = identifiers[1] if len(identifiers) > 1 else None
                value = declare_class(
                    context,
                    declaration,
                    identifiers[0],
                    superclass,
                )
                context.predeclared_symbols[id(declaration)] = (
                    value.symbol if isinstance(value.symbol, Symbol) else None
                )
            break
        pending_classes = remaining

    for declaration in class_declarations:
        class_symbol = context.predeclared_symbols.get(id(declaration))
        if class_symbol is None:
            continue
        context.class_stack.append(class_symbol)
        try:
            _predeclare_class_members(
                context,
                declaration,
                member_rule,
                field_rule,
                constant_rule,
                method_rule,
                identifier_token,
                type_rule,
                parameters_rule,
                recursive_parameters_alternative,
            )
        finally:
            context.class_stack.pop()

    for declaration in function_declarations:
        identifier = _find_child_by_token(declaration, identifier_token)
        value = _declare_function_from_tree(
            context,
            declaration,
            identifier,
            parameters_rule,
            recursive_parameters_alternative,
            identifier_token,
            type_rule,
        )
        context.predeclared_symbols[id(declaration)] = (
            value.symbol if isinstance(value.symbol, Symbol) else None
        )


def _declare_method_from_tree(
    context: SemanticContext,
    node: ParseTreeNode,
    name: object,
    parameters_rule: str = "",
    recursive_parameters_alternative: str = "",
    identifier_token: str = "",
    type_rule: str = "",
) -> SemanticValue:
    names, types, return_type = _signature_from_tree(
        node,
        parameters_rule,
        recursive_parameters_alternative,
        identifier_token,
        type_rule,
    )
    return declare_method(context, node, name, types, return_type, names)


def _find_member_declaration(
    wrapper: object,
    declaration_rules: set[str],
) -> object | None:
    for child in getattr(wrapper, "children", ()):
        if getattr(child, "rule_name", None) in declaration_rules:
            return child
    return None


def _find_descendant_by_rule(node: object, rule_name: str) -> object | None:
    for child in getattr(node, "children", ()):
        if getattr(child, "rule_name", None) == rule_name:
            return child
        match = _find_descendant_by_rule(child, rule_name)
        if match is not None:
            return match
    return None


def _predeclare_class_members(
    context: SemanticContext,
    node: ParseTreeNode,
    member_rule: str,
    field_rule: str,
    constant_rule: str,
    method_rule: str,
    identifier_token: str,
    type_rule: str,
    parameters_rule: str,
    recursive_parameters_alternative: str,
) -> None:
    if not context.class_stack or context.class_stack[-1] is None:
        return
    class_symbol = context.class_stack[-1]
    assert class_symbol is not None
    members = class_symbol.metadata["members"]
    declaration_rules = {field_rule, constant_rule, method_rule}
    for child in node.children:
        if child.rule_name != member_rule:
            continue
        declaration = _find_member_declaration(child, declaration_rules)
        if declaration is None:
            continue
        identifier = _find_child_by_token(declaration, identifier_token)
        name = str(getattr(identifier, "text", ""))
        if not name or name in members:
            continue
        location = context.location_of(declaration)
        if getattr(declaration, "rule_name", None) == method_rule:
            names, raw_types, raw_return = _signature_from_tree(
                declaration,
                parameters_rule,
                recursive_parameters_alternative,
                identifier_token,
                type_rule,
            )
            member_type: Type = FunctionType(
                tuple(context.resolve_type(type_) for type_ in raw_types),
                context.resolve_type(raw_return),
            )
            symbol = Symbol(
                name,
                SymbolKind.METHOD,
                member_type,
                False,
                location,
                {
                    "parameter_names": names,
                    "definition_scope": context.symbol_table.current_scope,
                },
            )
        else:
            type_node = _find_descendant_by_rule(declaration, type_rule)
            member_type = (
                context.resolve_type(_concatenated_text(type_node))
                if type_node is not None
                else UNKNOWN
            )
            symbol = Symbol(
                name,
                SymbolKind.FIELD,
                member_type,
                getattr(declaration, "rule_name", None) == field_rule,
                location,
            )
        members[name] = symbol


def _sequence_trimmed(
    context: SemanticContext,
    node: ParseTreeNode,
    statements: Iterable[object] = (),
    skip_start: int = 0,
    skip_end: int = 0,
) -> object:
    values = tuple(statements)
    children = tuple(node.children)
    value_end = len(values) - skip_end if skip_end else len(values)
    child_end = len(children) - skip_end if skip_end else len(children)
    proxy = SimpleNamespace(children=children[skip_start:child_end])
    return validate_sequence(
        context, proxy, values[skip_start:value_end]
    )


def register_composition_actions(registry: ActionRegistry) -> None:
    """Register safe action compositions required by declarative profiles.

    Args:
        registry: Allow-list that receives the stable action names.

    Returns:
        ``None``. The supplied registry is updated in place.

    Raises:
        ProfileError: If an action name is already registered.
    """
    registry.register("collection.start", _start_list)
    registry.register("collection.append", _append_list)
    registry.register("node.text", _node_text)
    registry.register("program.predeclare", _predeclare_program)
    registry.register("control.sequence_trimmed", _sequence_trimmed)
    registry.register("expression.array_collected", _build_array)
    registry.register("assignment.identifier", _assign_to_identifier)
    registry.register("assignment.member", _assign_to_member)
    registry.register("function.declare_from_tree", _declare_function_from_tree)
    registry.register("class.method_from_tree", _declare_method_from_tree)
    registry.register("class.predeclare_members", _predeclare_class_members)


__all__ = ["register_composition_actions"]

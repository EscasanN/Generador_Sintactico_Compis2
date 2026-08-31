"""Built-in, grammar-neutral actions and registry population."""

from __future__ import annotations

from src.semantic.action_registry import ActionRegistry
from src.semantic.actions.callables import register_callable_actions
from src.semantic.actions.classes import register_class_actions
from src.semantic.actions.control_flow import register_control_flow_actions
from src.semantic.actions.declarations import register_declaration_actions


def register_builtin_actions(registry: ActionRegistry) -> ActionRegistry:
    """Populate ``registry`` with every stable action owned by block 2."""
    register_declaration_actions(registry)
    register_callable_actions(registry)
    register_control_flow_actions(registry)
    register_class_actions(registry)
    return registry


__all__ = ["register_builtin_actions"]

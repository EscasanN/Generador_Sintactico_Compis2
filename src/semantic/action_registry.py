"""Allow-listed semantic actions referenced by declarative profiles."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.semantic.profile import ProfileError


ActionHandler = Callable[..., Any]


class ActionRegistry:
    """Register and resolve named Python callables without dynamic imports."""

    def __init__(self) -> None:
        self._handlers: dict[str, ActionHandler] = {}

    def register(self, name: str, handler: ActionHandler) -> None:
        """Register one stable name, rejecting duplicates and invalid handlers."""
        if not isinstance(name, str) or not name:
            raise ProfileError("action name must be a non-empty string")
        if not callable(handler):
            raise TypeError("action handler must be callable")
        if name in self._handlers:
            raise ProfileError(f"semantic action already registered: {name}")
        self._handlers[name] = handler

    def resolve(self, name: str) -> ActionHandler:
        """Resolve an allow-listed action or raise a profile error."""
        try:
            return self._handlers[name]
        except KeyError as exc:
            raise ProfileError(f"unknown semantic action: {name}") from exc

    @property
    def names(self) -> tuple[str, ...]:
        """Return registered names in insertion order."""
        return tuple(self._handlers)

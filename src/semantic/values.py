"""Framework-neutral values exchanged by semantic actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.semantic.diagnostics import SourceLocation
from src.semantic.types import Type


class SymbolReference(Protocol):
    """Structural contract for an optional symbol attached to a value.

    Args:
        None. Implementations are supplied by later semantic layers.

    Returns:
        Any object exposing a string ``name`` property satisfies the protocol.

    Raises:
        No exceptions are introduced by this protocol.
    """

    @property
    def name(self) -> str:
        """Return the source-level symbol name.

        Returns:
            The identifier exposed by the later symbol implementation.

        Raises:
            No exceptions are introduced by this protocol.
        """
        ...


@dataclass(frozen=True, slots=True)
class SemanticValue:
    """Carry the type and neutral metadata produced for an expression.

    Args:
        type: Static semantic type.
        constant_value: Optional compile-time literal value. ``None`` also
            represents the language's null literal.
        assignable: Whether this value denotes a legal assignment target.
        mutable: Whether that target may be changed after declaration.
        symbol: Optional structural symbol reference from a later layer.
        location: Optional one-based source location.

    Returns:
        An immutable value with no parser, grammar, profile, or GUI state.

    Raises:
        TypeError: If the required ``type`` argument is omitted.
    """

    type: Type
    constant_value: object | None = None
    assignable: bool = False
    mutable: bool = False
    symbol: SymbolReference | None = None
    location: SourceLocation | None = None

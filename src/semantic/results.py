"""Immutable public result produced by the generic semantic evaluator."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from src.semantic.diagnostics import Diagnostic, DiagnosticSeverity
from src.semantic.symbol_table import SymbolTable
from src.semantic.values import SemanticValue


@dataclass(frozen=True, slots=True)
class SemanticAnalysisResult:
    """Expose diagnostics, retained scopes, final value and traversal counts."""

    diagnostics: tuple[Diagnostic, ...]
    symbol_table: SymbolTable
    value: SemanticValue | None = None
    statistics: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(self, "statistics", MappingProxyType(dict(self.statistics)))

    @property
    def accepted(self) -> bool:
        """Return true when no semantic error was accumulated."""
        return not any(
            diagnostic.severity is DiagnosticSeverity.ERROR
            for diagnostic in self.diagnostics
        )

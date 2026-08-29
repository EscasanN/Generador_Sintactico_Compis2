"""Framework-neutral semantic diagnostics and source coordinates."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum


class DiagnosticSeverity(Enum):
    """Severity levels understood by semantic consumers.

    ``ERROR`` rejects semantic acceptance, while ``WARNING`` remains
    reportable without rejecting a result.

    Args:
        value: Serialized value used when resolving an enum member.

    Returns:
        The matching severity member.

    Raises:
        ValueError: If ``value`` does not identify a member.
    """

    ERROR = "error"
    WARNING = "warning"


class DiagnosticCategory(Enum):
    """Stable categories used to group semantic diagnostics.

    The enum is independent of parsers and presentation frameworks.

    Args:
        value: Serialized value used when resolving an enum member.

    Returns:
        The matching category member.

    Raises:
        ValueError: If ``value`` does not identify a member.
    """

    TYPE = "type"
    SCOPE = "scope"
    FUNCTION = "function"
    CONTROL_FLOW = "control_flow"
    CLASS = "class"
    ARRAY = "array"
    GENERAL = "general"


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Identify a one-based interval in an optional source file.

    Args:
        line: One-based starting line.
        column: One-based starting column.
        end_line: Optional one-based ending line.
        end_column: Optional one-based ending column.
        source_path: Optional source identity or filesystem path.

    Returns:
        An immutable source location.

    Raises:
        ValueError: If any supplied coordinate is less than one.
    """

    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None
    source_path: str | None = None

    def __post_init__(self) -> None:
        """Validate that every present public coordinate is one-based.

        Returns:
            None.

        Raises:
            ValueError: If a coordinate is less than one.
        """
        coordinates = (self.line, self.column, self.end_line, self.end_column)
        if any(coordinate is not None and coordinate < 1 for coordinate in coordinates):
            raise ValueError("source coordinates are based on 1")


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """Describe one semantic issue without causing a side effect.

    Args:
        category: Semantic domain that detected the issue.
        severity: Whether the issue is an error or warning.
        message: Human-readable explanation.
        location: One-based source location associated with the issue.

    Returns:
        An immutable diagnostic record.

    Raises:
        TypeError: If construction is attempted without required arguments.
    """

    category: DiagnosticCategory
    severity: DiagnosticSeverity
    message: str
    location: SourceLocation


class DiagnosticBag:
    """Accumulate diagnostics silently while preserving insertion order.

    Args:
        None.

    Returns:
        A mutable accumulator whose public views are immutable snapshots.

    Raises:
        No exceptions during normal accumulation.
    """

    def __init__(self) -> None:
        """Create an empty diagnostic collection.

        Returns:
            None.

        Raises:
            No exceptions.
        """
        self._items: list[Diagnostic] = []

    def add(
        self,
        category: DiagnosticCategory,
        message: str,
        location: SourceLocation,
        severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
    ) -> Diagnostic:
        """Append one diagnostic without printing or raising it.

        Args:
            category: Semantic domain that detected the issue.
            message: Human-readable explanation.
            location: One-based source location for the issue.
            severity: Error by default; callers may explicitly use warning.

        Returns:
            The diagnostic that was appended.

        Raises:
            No exceptions during normal accumulation.
        """
        diagnostic = Diagnostic(category, severity, message, location)
        self._items.append(diagnostic)
        return diagnostic

    def extend(self, diagnostics: Iterable[Diagnostic]) -> None:
        """Append diagnostics from any iterable in iteration order.

        Args:
            diagnostics: Diagnostic records to append.

        Returns:
            None.

        Raises:
            Any exception raised while consuming the supplied iterable.
        """
        self._items.extend(diagnostics)

    @property
    def items(self) -> tuple[Diagnostic, ...]:
        """Return an immutable snapshot of accumulated diagnostics.

        Returns:
            A tuple in insertion order.

        Raises:
            No exceptions.
        """
        return tuple(self._items)

    @property
    def has_errors(self) -> bool:
        """Report whether at least one accumulated item is an error.

        Returns:
            ``True`` when an error exists; otherwise ``False``.

        Raises:
            No exceptions.
        """
        return any(item.severity is DiagnosticSeverity.ERROR for item in self._items)

    def __iter__(self) -> Iterator[Diagnostic]:
        """Iterate over a stable snapshot in insertion order."""
        return iter(self.items)

    def __len__(self) -> int:
        """Return the number of accumulated diagnostics."""
        return len(self._items)

"""Tests for source locations and accumulated semantic diagnostics."""

from dataclasses import FrozenInstanceError

import pytest

from src.semantic.diagnostics import (
    Diagnostic,
    DiagnosticBag,
    DiagnosticCategory,
    DiagnosticSeverity,
    SourceLocation,
)


def test_source_location_uses_one_based_coordinates_and_is_immutable() -> None:
    """A zero coordinate must fail; valid public coordinates remain unchanged."""
    location = SourceLocation(
        line=1,
        column=2,
        end_line=3,
        end_column=4,
        source_path="sample.cps",
    )

    assert location == SourceLocation(1, 2, 3, 4, "sample.cps")
    with pytest.raises(FrozenInstanceError):
        location.line = 9  # type: ignore[misc]

    for field_name in ("line", "column", "end_line", "end_column"):
        arguments = {"line": 1, "column": 1, field_name: 0}
        with pytest.raises(ValueError, match="based on 1"):
            SourceLocation(**arguments)


def test_diagnostic_preserves_category_severity_message_and_location() -> None:
    """A diagnostic must retain every field needed by later result views."""
    location = SourceLocation(7, 11)
    diagnostic = Diagnostic(
        category=DiagnosticCategory.TYPE,
        severity=DiagnosticSeverity.WARNING,
        message="possible loss of precision",
        location=location,
    )

    assert diagnostic.category is DiagnosticCategory.TYPE
    assert diagnostic.severity is DiagnosticSeverity.WARNING
    assert diagnostic.message == "possible loss of precision"
    assert diagnostic.location is location
    assert DiagnosticCategory.CONTROL_FLOW.value == "control_flow"
    assert DiagnosticCategory.ARRAY.value == "array"


def test_diagnostic_bag_accumulates_in_order_without_printing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Independent semantic errors must accumulate silently in source order."""
    bag = DiagnosticBag()
    first = bag.add(
        DiagnosticCategory.TYPE,
        "invalid operand",
        SourceLocation(1, 1),
    )
    warning = Diagnostic(
        DiagnosticCategory.GENERAL,
        DiagnosticSeverity.WARNING,
        "unusual expression",
        SourceLocation(2, 1),
    )
    last = Diagnostic(
        DiagnosticCategory.ARRAY,
        DiagnosticSeverity.ERROR,
        "invalid index",
        SourceLocation(3, 1),
    )
    bag.extend(item for item in (warning, last))

    assert first.severity is DiagnosticSeverity.ERROR
    assert bag.items == (first, warning, last)
    assert tuple(bag) == bag.items
    assert len(bag) == 3
    assert bag.has_errors is True
    assert capsys.readouterr() == ("", "")


def test_diagnostic_bag_exposes_an_immutable_snapshot() -> None:
    """Previously obtained item views must not change with later additions."""
    bag = DiagnosticBag()
    bag.add(
        DiagnosticCategory.GENERAL,
        "warning",
        SourceLocation(1, 1),
        DiagnosticSeverity.WARNING,
    )
    snapshot = bag.items

    bag.add(DiagnosticCategory.TYPE, "error", SourceLocation(2, 1))

    assert isinstance(snapshot, tuple)
    assert len(snapshot) == 1
    assert bag.has_errors is True


def test_warning_only_bag_does_not_report_errors() -> None:
    """Warnings alone must not make a semantic result fail acceptance."""
    bag = DiagnosticBag()
    bag.add(
        DiagnosticCategory.GENERAL,
        "warning",
        SourceLocation(1, 1),
        severity=DiagnosticSeverity.WARNING,
    )

    assert bag.has_errors is False

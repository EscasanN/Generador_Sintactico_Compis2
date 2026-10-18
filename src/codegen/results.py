"""Immutable results of intermediate-code generation and of a whole compilation.

``IntermediateCodeResult`` never exposes partial TAC: a rejected generation has
diagnostics and neither program nor text. ``CompilationResult`` only carries an
intermediate result when syntax and semantics were accepted (PIPE-01…PIPE-05).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from src.antlr_mode.runner import AntlrAnalysisResult
from src.codegen.activation import ActivationRecordLayout, RuntimeLayouts
from src.codegen.ir import IRProgram, OpCode, OperandKind
from src.codegen.layout import SymbolLayoutTable
from src.codegen.verifier import IRDiagnostic
from src.semantic.results import SemanticAnalysisResult


@dataclass(frozen=True, slots=True)
class IntermediateCodeResult:
    """Verified TAC, the extended symbol table, activation records and statistics."""

    program: IRProgram | None
    text: str = ""
    diagnostics: tuple[IRDiagnostic, ...] = ()
    layouts: RuntimeLayouts | None = None
    statistics: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(self, "statistics", MappingProxyType(dict(self.statistics)))
        if self.diagnostics and (self.program is not None or self.text):
            raise ValueError("a rejected generation must not expose TAC")
        if self.program is None and self.text:
            raise ValueError("TAC text requires its structured program")

    @classmethod
    def rejected(cls, diagnostics: tuple[IRDiagnostic, ...]) -> "IntermediateCodeResult":
        if not diagnostics:
            raise ValueError("a rejected generation needs at least one diagnostic")
        return cls(None, "", diagnostics)

    @property
    def accepted(self) -> bool:
        """A program exists, has text and passed ``IRVerifier`` without errors."""
        return self.program is not None and bool(self.text) and not self.diagnostics

    @property
    def symbol_layouts(self) -> SymbolLayoutTable | None:
        return self.layouts.symbols if self.layouts is not None else None

    @property
    def activation_records(self) -> tuple[ActivationRecordLayout, ...]:
        """Global frame first, then one record per procedure."""
        if self.layouts is None:
            return ()
        return (self.layouts.global_frame, *self.layouts.frames)


@dataclass(frozen=True, slots=True)
class CompilationResult:
    """Every phase of one compilation; later phases exist only after earlier ones pass."""

    syntax_result: AntlrAnalysisResult
    semantic_result: SemanticAnalysisResult | None = None
    intermediate_result: IntermediateCodeResult | None = None
    source_path: Path | None = None

    def __post_init__(self) -> None:
        if self.intermediate_result is not None and (
            not self.syntax_result.accepted
            or self.semantic_result is None
            or not self.semantic_result.accepted
        ):
            raise ValueError("TAC is generated only after syntax and semantics are accepted")

    @property
    def accepted(self) -> bool:
        return self.failed_stage is None

    @property
    def failed_stage(self) -> str | None:
        """``"syntax"``, ``"semantic"`` or ``"codegen"``; ``None`` when accepted."""
        if not self.syntax_result.accepted:
            return "syntax"
        if self.semantic_result is None or not self.semantic_result.accepted:
            return "semantic"
        if self.intermediate_result is None or not self.intermediate_result.accepted:
            return "codegen"
        return None

    @property
    def tac(self) -> str:
        """The verified TAC text, or an empty string when any phase failed."""
        if not self.accepted or self.intermediate_result is None:
            return ""
        return self.intermediate_result.text


def program_statistics(program: IRProgram, global_temporary_peak: int) -> dict[str, int]:
    """Instructions, procedures, labels, temporaries created and peak of live temporaries."""
    units = (program.global_code, *(p.instructions for p in program.procedures))
    leases = {
        operand.lease
        for unit in units
        for item in unit
        for operand in (item.arg1, item.arg2, item.result)
        if operand is not None and operand.kind is OperandKind.TEMPORARY
    }
    return {
        "instructions": sum(len(unit) for unit in units),
        "procedures": len(program.procedures),
        "labels": sum(1 for unit in units for item in unit if item.opcode is OpCode.LABEL),
        "temporaries_created": len(leases),
        "temporary_peak": max(
            [global_temporary_peak, *(p.temporary_peak for p in program.procedures)]
        ),
    }

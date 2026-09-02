"""Runtime support for loading ANTLR `.g4` grammars from the IDE."""

from src.antlr_mode.grammar_info import (
    GrammarInfo,
    GrammarInfoError,
    inspect_g4,
    parse_g4_info,
)
from src.antlr_mode.runner import (
    AntlrAnalysisResult,
    AntlrDiagnostic,
    AntlrModeError,
    AntlrRuntimeSession,
    AntlrToken,
    analyze_with_g4,
)

__all__ = [
    "AntlrAnalysisResult",
    "AntlrDiagnostic",
    "AntlrModeError",
    "AntlrRuntimeSession",
    "AntlrToken",
    "GrammarInfo",
    "GrammarInfoError",
    "analyze_with_g4",
    "inspect_g4",
    "parse_g4_info",
]

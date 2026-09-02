"""Public integration boundary between the ANTLR frontend and semantics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.antlr_mode.runner import AntlrAnalysisResult, analyze_with_g4
from src.semantic.profile import ProfileError, load_profile, validate_profile
from src.semantic.results import SemanticAnalysisResult


class SemanticAdapterError(RuntimeError):
    """Report an invalid profile, unavailable runtime, or incompatible tree."""


@dataclass(frozen=True, slots=True)
class SemanticRunRequest:
    """Describe one parser and semantic-analysis request."""

    grammar_path: str | Path
    source: str
    profile_path: str | Path
    start_rule: str | None = None
    source_path: str | Path | None = None


@dataclass(frozen=True, slots=True)
class SemanticRunResult:
    """Bundle syntax and optional semantics for GUI or CLI consumers."""

    syntax_result: AntlrAnalysisResult
    semantic_result: SemanticAnalysisResult | None = None

    @property
    def accepted(self) -> bool:
        """Accept only when both frontend and semantic stages succeed."""
        return (
            self.syntax_result.accepted
            and self.semantic_result is not None
            and self.semantic_result.accepted
        )


def analyze_semantics_with_g4(
    grammar_path: str | Path,
    source: str,
    profile_path: str | Path,
    start_rule: str | None = None,
    source_path: str | Path | None = None,
) -> SemanticRunResult:
    """Run syntax first, then walk the native ANTLR tree when it is valid."""
    request = SemanticRunRequest(
        grammar_path=grammar_path,
        source=source,
        profile_path=profile_path,
        start_rule=start_rule,
        source_path=source_path,
    )
    syntax_result = analyze_with_g4(
        request.grammar_path,
        request.source,
        request.start_rule,
    )
    if not syntax_result.accepted:
        return SemanticRunResult(syntax_result=syntax_result)
    if syntax_result.tree is None or syntax_result.native_tree is None:
        raise SemanticAdapterError(
            "ANTLR accepted the input but did not retain both tree representations"
        )
    if not syntax_result.rule_names:
        raise SemanticAdapterError(
            "ANTLR accepted the input but did not retain parser rule names"
        )

    try:
        profile = load_profile(request.profile_path)
        validate_profile(profile, syntax_result.grammar.parser_rules)
    except ProfileError as exc:
        raise SemanticAdapterError(f"invalid semantic profile: {exc}") from exc

    try:
        from antlr4 import ParseTreeWalker
        from src.semantic.antlr_listener import (
            SemanticListenerError,
            SemanticTreeListener,
        )
    except ImportError as exc:
        raise SemanticAdapterError(
            "antlr4-python3-runtime is required for semantic tree traversal"
        ) from exc

    listener = None
    try:
        listener = SemanticTreeListener(
            native_tree=syntax_result.native_tree,
            common_tree=syntax_result.tree,
            rule_names=syntax_result.rule_names,
            profile=profile,
            source_path=(
                str(request.source_path)
                if request.source_path is not None
                else None
            ),
        )
        ParseTreeWalker.DEFAULT.walk(listener, syntax_result.native_tree)
        semantic_result = listener.result
    except (ProfileError, SemanticListenerError) as exc:
        if listener is not None:
            listener.abort()
        raise SemanticAdapterError(f"semantic traversal failed: {exc}") from exc
    return SemanticRunResult(
        syntax_result=syntax_result,
        semantic_result=semantic_result,
    )


__all__ = [
    "SemanticAdapterError",
    "SemanticRunRequest",
    "SemanticRunResult",
    "analyze_semantics_with_g4",
]

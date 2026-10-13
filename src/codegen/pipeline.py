"""Public compilation pipeline: syntax, semantics, then verified TAC (block 3).

``compile_compiscript`` is the single entry point consumers (CLI and IDE) need:

1. ``analyze_semantics_with_g4`` (syntax first, semantics only if it passes);
2. a syntax or semantic error stops here, without any intermediate result;
3. facts and layouts, then ``CompiscriptCodeGenerator``;
4. ``IRVerifier``; only verified IR is formatted as TAC.

Codegen contract failures (``CodegenError``, ``LayoutError``, a missing semantic
fact) become IR diagnostics. Any other exception is a bug and propagates: it is
never turned into an accepted compilation.
"""

from __future__ import annotations

from pathlib import Path

from src.antlr_mode.parse_tree import ParseTreeNode
from src.codegen.contracts import CodegenError
from src.codegen.formatter import format_program
from src.codegen.generator import CompiscriptCodeGenerator
from src.codegen.layout import LayoutError
from src.codegen.results import CompilationResult, IntermediateCodeResult, program_statistics
from src.codegen.semantic_facts import MissingFactError, SemanticFactsIndex
from src.codegen.verifier import IRDiagnostic, IRVerifier
from src.semantic.antlr_adapter import analyze_semantics_with_g4
from src.semantic.results import SemanticAnalysisResult

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GRAMMAR_PATH = REPOSITORY_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
PROFILE_PATH = REPOSITORY_ROOT / "semantic_profiles" / "compiscript.semantic.json"
START_RULE = "program"


def compile_compiscript(
    source: str,
    source_path: str | Path | None = None,
    *,
    grammar_path: str | Path = GRAMMAR_PATH,
    profile_path: str | Path = PROFILE_PATH,
) -> CompilationResult:
    """Compile Compiscript source to verified TAC, or report why it was rejected."""
    path = Path(source_path) if source_path is not None else None
    run = analyze_semantics_with_g4(grammar_path, source, profile_path, START_RULE, source_path)
    syntax, semantic = run.syntax_result, run.semantic_result
    if (
        not syntax.accepted
        or syntax.tree is None
        or semantic is None
        or not semantic.accepted
    ):
        return CompilationResult(syntax, semantic, None, path)
    intermediate = generate_intermediate_code(semantic, syntax.tree)
    return CompilationResult(syntax, semantic, intermediate, path)


def generate_intermediate_code(
    semantic_result: SemanticAnalysisResult, tree: ParseTreeNode
) -> IntermediateCodeResult:
    """Lower an accepted analysis, verify it and format it; never partial TAC."""
    if not semantic_result.accepted:
        raise ValueError("TAC is generated only for an accepted semantic result")
    try:
        facts = SemanticFactsIndex.from_result(semantic_result, tree)
        generated = CompiscriptCodeGenerator(facts).generate(tree)
    except CodegenError as error:
        message = str(error).removeprefix(f"{error.code}: ")
        return IntermediateCodeResult.rejected((IRDiagnostic(error.code, message, error.location),))
    except MissingFactError as error:
        return IntermediateCodeResult.rejected((IRDiagnostic("IRGEN-MISSING-FACT", str(error)),))
    except LayoutError as error:
        return IntermediateCodeResult.rejected((IRDiagnostic("IRGEN-LAYOUT", str(error)),))
    diagnostics = IRVerifier().verify(generated.program)
    if diagnostics:
        return IntermediateCodeResult.rejected(diagnostics)
    return IntermediateCodeResult(
        generated.program,
        format_program(generated.program),
        (),
        generated.layouts,
        program_statistics(generated.program, generated.global_temporary_peak),
    )

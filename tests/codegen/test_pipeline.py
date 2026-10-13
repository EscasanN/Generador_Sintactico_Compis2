"""compile_compiscript: phase order, rejection without TAC and full coverage (PIPE-01…05, EXT-08)."""

import re
from pathlib import Path

import pytest

from src.codegen import pipeline
from src.codegen.expression_lowering import _BINARY, _LITERALS, _UNARY, _WRAPPERS
from src.codegen.generator import CompiscriptCodeGenerator
from src.codegen.ir import IRProgram, OpCode
from src.codegen.pipeline import GRAMMAR_PATH, compile_compiscript, generate_intermediate_code
from src.codegen.results import CompilationResult, IntermediateCodeResult
from src.codegen.verifier import IRDiagnostic, IRVerifier
from src.semantic.diagnostics import DiagnosticSeverity

REPO_ROOT = Path(__file__).resolve().parents[2]
CPS = REPO_ROOT / "tests" / "cps"
ACCEPTED = sorted(
    [*(CPS / "validos").glob("*.cps"), *(CPS / "advertencias").glob("*.cps"),
     CPS / "demostracion-valida.cps"]
)
REJECTED = sorted([*(CPS / "invalidos").glob("*.cps"), CPS / "demostracion-invalida.cps"])


def compile_file(path: Path):
    return compile_compiscript(path.read_text(encoding="utf8"), path)


# -- phase order ------------------------------------------------------------------


def test_syntax_error_stops_before_semantics_and_tac():
    """PIPE-01."""
    result = compile_compiscript("let x: integer = ;\n")
    assert result.failed_stage == "syntax" and not result.accepted
    assert result.semantic_result is None and result.intermediate_result is None
    assert result.tac == ""


def test_semantic_error_stops_before_tac():
    """PIPE-02."""
    result = compile_compiscript('let x: integer = "texto";\n')
    assert result.failed_stage == "semantic"
    assert result.semantic_result is not None and result.semantic_result.diagnostics
    assert result.intermediate_result is None and result.tac == ""


@pytest.mark.parametrize("path", sorted((CPS / "advertencias").glob("*.cps")), ids=lambda p: p.name)
def test_warnings_still_produce_tac(path):
    """PIPE-03: a warning (unreachable code) never blocks code generation."""
    result = compile_file(path)
    severities = {d.severity for d in result.semantic_result.diagnostics}
    assert severities == {DiagnosticSeverity.WARNING}
    assert result.accepted and result.tac.startswith("global:")


def test_codegen_error_rejects_the_compilation_without_tac():
    """PIPE-04: an IRGEN diagnostic, with location, and no partial program."""
    result = compile_compiscript("class C {\n  let v: integer;\n}\nlet x: integer = C.v;\n")
    assert result.semantic_result.accepted
    assert result.failed_stage == "codegen" and result.tac == ""
    intermediate = result.intermediate_result
    assert intermediate.program is None and intermediate.text == "" and not intermediate.accepted
    (diagnostic,) = intermediate.diagnostics
    assert diagnostic.code == "IRGEN-UNSUPPORTED-NODE" and diagnostic.location.line == 4
    assert not diagnostic.message.startswith("IRGEN-")


def test_verifier_errors_reject_the_compilation(monkeypatch):
    """PIPE-04: output that fails IRVerifier is never published."""

    class RejectingVerifier:
        def verify(self, program):
            return (IRDiagnostic("IR-TEST", "rejected on purpose"),)

    monkeypatch.setattr(pipeline, "IRVerifier", RejectingVerifier)
    result = compile_compiscript("let a: integer = 1;\n")
    assert result.failed_stage == "codegen"
    assert [d.code for d in result.intermediate_result.diagnostics] == ["IR-TEST"]
    assert result.intermediate_result.program is None


def test_valid_program_exposes_tac_layouts_frames_and_statistics():
    """PIPE-05 with the full demonstration program."""
    result = compile_file(CPS / "demostracion-valida.cps")
    assert result.accepted and result.failed_stage is None
    assert result.source_path == CPS / "demostracion-valida.cps"
    intermediate = result.intermediate_result
    program = intermediate.program
    assert IRVerifier().verify(program) == ()
    assert result.tac == intermediate.text and "procedure Counter.description(" in result.tac
    labels = [frame.label for frame in intermediate.activation_records]
    assert labels[0] == "global"
    assert {"fn_isEven", "Counter.constructor", "BaseCounter.constructor"} <= set(labels)
    peaks = {p.label.value: p.temporary_peak for p in program.procedures}
    for frame in intermediate.activation_records[1:]:
        assert frame.temporary_capacity == peaks[frame.label]
    names = {row["name"] for row in intermediate.symbol_layouts.rows()}
    assert {"counter", "values", "isEven", "Counter"} <= names
    stats = intermediate.statistics
    assert stats["procedures"] == len(program.procedures)
    assert stats["instructions"] == len(program.global_code) + sum(
        len(p.instructions) for p in program.procedures
    )
    assert stats["labels"] == sum(
        1 for unit in (program.global_code, *(p.instructions for p in program.procedures))
        for item in unit if item.opcode is OpCode.LABEL
    )
    assert stats["temporary_peak"] >= max(peaks.values())
    assert stats["temporaries_created"] >= stats["temporary_peak"]


# -- every demonstration program --------------------------------------------------


@pytest.mark.parametrize("path", ACCEPTED, ids=lambda p: p.name)
def test_every_valid_program_compiles_to_verified_tac(path):
    result = compile_file(path)
    assert result.accepted, result.intermediate_result and result.intermediate_result.diagnostics
    assert IRVerifier().verify(result.intermediate_result.program) == ()


@pytest.mark.parametrize("path", REJECTED, ids=lambda p: p.name)
def test_every_invalid_program_is_rejected_without_tac(path):
    result = compile_file(path)
    assert not result.accepted and result.failed_stage in ("syntax", "semantic")
    assert result.intermediate_result is None and result.tac == ""


def test_compilation_is_deterministic():
    source = (CPS / "validos" / "FUN-04-closure.cps").read_text(encoding="utf8")
    assert compile_compiscript(source).tac == compile_compiscript(source).tac


# -- result invariants ------------------------------------------------------------


def test_intermediate_result_never_holds_partial_tac():
    diagnostic = IRDiagnostic("IR-TEST", "x")
    with pytest.raises(ValueError):
        IntermediateCodeResult(IRProgram(), "global:", (diagnostic,))
    with pytest.raises(ValueError):
        IntermediateCodeResult(None, "global:")
    with pytest.raises(ValueError):
        IntermediateCodeResult.rejected(())
    rejected = IntermediateCodeResult.rejected((diagnostic,))
    assert not rejected.accepted and rejected.activation_records == ()
    assert rejected.symbol_layouts is None


def test_compilation_result_refuses_tac_after_a_failed_phase():
    rejected = compile_compiscript('let x: integer = "texto";\n')
    accepted = compile_compiscript("let a: integer = 1;\n")
    with pytest.raises(ValueError):
        CompilationResult(
            rejected.syntax_result, rejected.semantic_result, accepted.intermediate_result
        )
    with pytest.raises(ValueError):
        generate_intermediate_code(rejected.semantic_result, rejected.syntax_result.tree)


def test_results_are_immutable():
    result = compile_compiscript("let a: integer = 1;\n")
    with pytest.raises(AttributeError):
        result.intermediate_result.text = "otro"
    with pytest.raises(TypeError):
        result.intermediate_result.statistics["procedures"] = 3


# -- coverage and dependencies ----------------------------------------------------


def _grammar_rules():
    text = GRAMMAR_PATH.read_text(encoding="utf8")
    parser = text.split("// Lexer Rules")[0]
    return {
        name: body
        for name, body in re.findall(r"^([a-z]\w*)\s*:(.*?);\s*$", parser, re.M | re.S)
    }


EXPRESSION_RULES = (
    "assignmentExpr", "conditionalExpr", "logicalOrExpr", "logicalAndExpr", "equalityExpr",
    "relationalExpr", "additiveExpr", "multiplicativeExpr", "unaryExpr", "primaryExpr",
    "literalExpr", "leftHandSide", "primaryAtom", "arrayLiteral",
)


def test_every_statement_and_expression_alternative_has_a_handler():
    """EXT-08: no grammar alternative can reach codegen without lowering."""
    rules = _grammar_rules()
    statements = [alt.strip() for alt in rules["statement"].split("|")]
    handled_statements = set(CompiscriptCodeGenerator.STATEMENTS)
    for rule in statements:
        labels = re.findall(r"#\s*(\w+)", rules[rule])
        assert rule in handled_statements or (labels and set(labels) <= handled_statements), rule
    handled_expressions = (
        set(CompiscriptCodeGenerator.EXPRESSIONS) | set(_BINARY) | set(_UNARY)
        | set(_LITERALS) | set(_WRAPPERS) | {"AndExpr", "OrExpr", "TernaryExpr"}
    )
    labels = [label for rule in EXPRESSION_RULES for label in re.findall(r"#\s*(\w+)", rules[rule])]
    assert len(labels) > 40
    missing = [label for label in labels if label not in handled_expressions]
    assert missing == []


def test_codegen_package_does_not_depend_on_qt():
    for module in (REPO_ROOT / "src" / "codegen").glob("*.py"):
        assert "PyQt6" not in module.read_text(encoding="utf8"), module.name

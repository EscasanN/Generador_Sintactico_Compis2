"""Executable evidence from ``tests/cps/codegen`` (TST-01, TST-02, TST-03).

Every fixture starts with two header comments:

* ``// IDs: ...`` -- the matrix IDs it demonstrates;
* ``// Esperado: ACCEPT`` or ``// Esperado: REJECT <syntax|semantic|codegen> [CODE]``.

Valid programs must produce verified TAC; invalid ones must stop in the declared
phase without TAC. Golden ``.tac`` files are reserved for representative
programs; the rest is checked on the structured IR so format tweaks do not make
the whole suite fragile.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.codegen.ir import OpCode
from src.codegen.pipeline import compile_compiscript
from src.codegen.verifier import IRVerifier
from src.main import tac_document
from src.semantic.diagnostics import DiagnosticSeverity

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "cps" / "codegen"
VALID = sorted((FIXTURES / "validos").glob("*.cps"))
INVALID = sorted((FIXTURES / "invalidos").glob("*.cps"))
GOLDEN = sorted((FIXTURES / "esperados").glob("*.tac"))

_IDS = re.compile(r"^// IDs: (.+)$", re.MULTILINE)
_EXPECTED = re.compile(r"^// Esperado: (.+)$", re.MULTILINE)

# Matrix IDs whose positive evidence is a .cps compiled end to end.
REQUIRED_POSITIVE_IDS = {
    *(f"EXP-0{n}" for n in range(1, 9)),
    *(f"CTL-0{n}" for n in range(1, 9)),
    *(f"FUN-0{n}" for n in range(1, 10)),
    *(f"CLS-0{n}" for n in range(1, 7)),
    *(f"LST-0{n}" for n in range(1, 5)),
    *(f"TMP-0{n}" for n in range(1, 6)),
    "PIPE-03", "PIPE-05",
    *(f"EXT-0{n}" for n in range(1, 8)),
}
REQUIRED_NEGATIVE_STAGES = {"syntax", "semantic", "codegen"}


def _header(path: Path) -> tuple[set[str], list[str]]:
    text = path.read_text(encoding="utf-8")
    ids, expected = _IDS.search(text), _EXPECTED.search(text)
    assert ids and expected, f"{path.name} needs '// IDs:' and '// Esperado:' headers"
    return {item.strip() for item in ids.group(1).split(",")}, expected.group(1).split()


def _compile(path: Path):
    return compile_compiscript(path.read_text(encoding="utf-8"), path)


def _opcodes(result) -> set[OpCode]:
    program = result.intermediate_result.program
    units = (program.global_code, *(p.instructions for p in program.procedures))
    return {instruction.opcode for unit in units for instruction in unit}


# -- inventory ------------------------------------------------------------------


def test_fixture_folders_are_populated():
    assert len(VALID) >= 10 and len(INVALID) >= 5 and len(GOLDEN) >= 3


@pytest.mark.parametrize("path", [*VALID, *INVALID], ids=lambda p: p.name)
def test_every_fixture_declares_ids_and_expected_outcome(path):
    ids, expected = _header(path)
    assert ids and all(re.fullmatch(r"[A-Z]+-\d{2}", item) for item in ids)
    prefix = path.name.split("-")[0]
    assert prefix == "DEMO" or prefix in {item.split("-")[0] for item in ids}
    folder = path.parent.name
    assert expected[0] == ("ACCEPT" if folder == "validos" else "REJECT")
    if expected[0] == "REJECT":
        assert expected[1] in REQUIRED_NEGATIVE_STAGES


def test_valid_fixtures_cover_every_mandatory_matrix_id():
    """TST-01: one positive .cps per required matrix ID."""
    covered = set().union(*(_header(path)[0] for path in VALID))
    assert REQUIRED_POSITIVE_IDS - covered == set()


def test_invalid_fixtures_cover_every_failing_phase():
    """TST-02: at least one rejected fixture per compilation phase."""
    stages = {_header(path)[1][1] for path in INVALID}
    assert stages == REQUIRED_NEGATIVE_STAGES


# -- positive and negative outcomes ---------------------------------------------


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.name)
def test_valid_fixture_produces_verified_tac_layouts_and_frames(path):
    result = _compile(path)
    errors = [
        d for d in result.semantic_result.diagnostics if d.severity is DiagnosticSeverity.ERROR
    ]
    assert result.accepted, (errors, result.intermediate_result)
    intermediate = result.intermediate_result
    assert IRVerifier().verify(intermediate.program) == ()
    assert result.tac.startswith("global:")
    assert intermediate.symbol_layouts is not None and len(intermediate.symbol_layouts) > 0
    frames = intermediate.activation_records
    assert frames[0].label == "global"
    assert len(frames) == len(intermediate.program.procedures) + 1


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.name)
def test_invalid_fixture_stops_in_its_phase_without_tac(path):
    _, expected = _header(path)
    stage = expected[1]
    result = _compile(path)
    assert not result.accepted
    assert result.failed_stage == stage
    assert result.tac == ""
    if stage == "syntax":
        assert result.syntax_result.diagnostics
        assert result.semantic_result is None and result.intermediate_result is None
    elif stage == "semantic":
        assert any(
            d.severity is DiagnosticSeverity.ERROR for d in result.semantic_result.diagnostics
        )
        assert result.intermediate_result is None
    else:
        intermediate = result.intermediate_result
        assert intermediate.program is None and intermediate.text == ""
        codes = [diagnostic.code for diagnostic in intermediate.diagnostics]
        assert codes and (len(expected) < 3 or expected[2] in codes)
        assert all(d.location is not None for d in intermediate.diagnostics)


# -- golden TAC -----------------------------------------------------------------


@pytest.mark.parametrize("golden", GOLDEN, ids=lambda p: p.name)
def test_golden_tac_matches_the_compiler_output(golden):
    """TST-03: representative programs keep a stable, reviewed TAC text."""
    source = FIXTURES / "validos" / f"{golden.stem}.cps"
    assert source.is_file(), f"{golden.name} has no source program"
    result = _compile(source)
    assert result.accepted
    expected = golden.read_text(encoding="utf-8")
    assert tac_document(result.tac) == expected, (
        f"TAC changed for {source.name}; if intended, regenerate with: "
        f"python -m src.main --cps {source.relative_to(REPO_ROOT).as_posix()} "
        f"--emit-tac {golden.relative_to(REPO_ROOT).as_posix()}"
    )


def test_demo_has_a_golden_file():
    assert (FIXTURES / "esperados" / "DEMO-completa.tac") in GOLDEN


# -- structural evidence per domain ---------------------------------------------


@pytest.mark.parametrize(
    ("name", "opcodes"),
    [
        ("EXP-01-aritmetica", {OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, OpCode.MOD,
                               OpCode.NEG, OpCode.NOT, OpCode.CAST}),
        ("EXP-03-logicas", {OpCode.EQ, OpCode.NE, OpCode.LT, OpCode.LE, OpCode.GT, OpCode.GE,
                            OpCode.IF_TRUE, OpCode.IF_FALSE, OpCode.LABEL}),
        ("EXP-05-asignaciones", {OpCode.FIELD_SET, OpCode.LIST_SET, OpCode.OBJECT_NEW}),
        ("CTL-03-bucles", {OpCode.GOTO, OpCode.IF_FALSE, OpCode.IF_TRUE, OpCode.LABEL}),
        ("FUN-01-funciones", {OpCode.PARAM, OpCode.CALL, OpCode.RETURN}),
        ("FUN-07-closures", {OpCode.ENV_NEW, OpCode.ENV_SET, OpCode.ENV_GET, OpCode.CLOSURE,
                             OpCode.CLOSURE_CALL}),
        ("CLS-01-objetos", {OpCode.OBJECT_NEW, OpCode.FIELD_GET, OpCode.FIELD_SET, OpCode.CALL}),
        ("LST-01-listas", {OpCode.LIST_NEW, OpCode.LIST_GET, OpCode.LIST_SET, OpCode.LIST_LEN}),
        ("EXT-01-print-try", {OpCode.TRY_BEGIN, OpCode.TRY_END, OpCode.CATCH}),
    ],
)
def test_domain_fixture_emits_its_specialised_instructions(name, opcodes):
    result = _compile(FIXTURES / "validos" / f"{name}.cps")
    assert opcodes <= _opcodes(result)


def test_tmp_fixture_recycles_temporaries_and_frames_reserve_the_peak():
    """TMP-02 / TMP-05: far fewer live slots than temporaries created."""
    result = _compile(FIXTURES / "validos" / "TMP-01-reciclaje.cps")
    stats = result.intermediate_result.statistics
    assert stats["temporary_peak"] < stats["temporaries_created"]
    global_frame = result.intermediate_result.activation_records[0]
    assert global_frame.temporary_capacity == stats["temporary_peak"]


def test_recursive_fixture_calls_its_own_label():
    """FUN-05 / FUN-06: recursion reuses the procedure label."""
    result = _compile(FIXTURES / "validos" / "FUN-05-recursion.cps")
    for procedure in result.intermediate_result.program.procedures:
        if str(procedure.label) in {"fn_factorial", "fn_fibonacci"}:
            targets = {
                str(item.arg1) for item in procedure.instructions if item.opcode is OpCode.CALL
            }
            assert str(procedure.label) in targets


def test_closure_fixture_frames_separate_control_and_access_links():
    """FUN-08 / FUN-09 / RUN-03: nested frames expose both links and captures."""
    result = _compile(FIXTURES / "validos" / "FUN-07-closures.cps")
    frames = {frame.label: frame for frame in result.intermediate_result.activation_records}
    inner = frames["fn_contador.incrementar.doble"]
    assert {slot.name for slot in inner.header} >= {"control_link", "access_link"}
    assert inner.level == 3
    capture = next(c for c in inner.captures if c.symbol.name == "cuenta")
    assert capture.owner_frame == "fn_contador" and capture.depth == 1


def test_switch_fixture_evaluates_the_discriminant_once():
    """CTL-06: one ADD for ``opcion + 1`` in the whole global code."""
    result = _compile(FIXTURES / "validos" / "CTL-06-switch.cps")
    adds = [i for i in result.intermediate_result.program.global_code if i.opcode is OpCode.ADD]
    assert len(adds) == 2  # opcion + 1 (discriminant) and resultado + "!"

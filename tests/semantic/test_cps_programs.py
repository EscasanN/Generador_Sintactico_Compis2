"""Compile the presentation-ready CPS programs as executable evidence."""

from pathlib import Path

import pytest

from src.semantic.antlr_adapter import analyze_semantics_with_g4
from src.semantic.symbol_table import ScopeKind


REPO_ROOT = Path(__file__).resolve().parents[2]
GRAMMAR = REPO_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
PROFILE = REPO_ROOT / "semantic_profiles" / "compiscript.semantic.json"
CPS_ROOT = REPO_ROOT / "tests" / "cps"

VALID_PROGRAMS = (
    "demostracion-valida.cps",
    "validos/TYP-01-aritmetica.cps",
    "validos/TYP-02-logica.cps",
    "validos/TYP-03-comparaciones.cps",
    "validos/TYP-04-asignacion.cps",
    "validos/TYP-05-constante.cps",
    "validos/TYP-06-estructuras.cps",
    "validos/SCP-01-resolucion.cps",
    "validos/SCP-02-shadowing.cps",
    "validos/SCP-03-bloques-anidados.cps",
    "validos/SCP-04-entornos.cps",
    "validos/FUN-01-argumentos.cps",
    "validos/FUN-02-retorno.cps",
    "validos/FUN-03-recursion.cps",
    "validos/FUN-04-closure.cps",
    "validos/FUN-05-nombres-distintos.cps",
    "validos/CTL-01-condiciones.cps",
    "validos/CTL-02-bucles.cps",
    "validos/CTL-03-return.cps",
    "validos/CTL-04-catch.cps",
    "validos/CLS-01-miembros.cps",
    "validos/CLS-02-constructor.cps",
    "validos/CLS-03-this.cps",
    "validos/CLS-04-herencia.cps",
    "validos/LST-01-lista-homogenea.cps",
    "validos/LST-02-indice-entero.cps",
    "validos/GEN-01-flujo-alcanzable.cps",
    "validos/GEN-02-expresiones.cps",
    "validos/GEN-03-nombres.cps",
    "validos/EXT-01-endurecimiento.cps",
)

ERROR_PROGRAMS = (
    ("invalidos/TYP-01-aritmetica-booleana.cps", "semantic", "type"),
    ("invalidos/TYP-02-logica-no-booleana.cps", "semantic", "type"),
    ("invalidos/TYP-03-comparacion-incompatible.cps", "semantic", "type"),
    ("invalidos/TYP-04-asignacion-incompatible.cps", "semantic", "type"),
    ("invalidos/TYP-05-constante-sin-inicializar.cps", "syntax", None),
    ("invalidos/TYP-06-estructura-incompatible.cps", "semantic", "array"),
    ("invalidos/SCP-01-no-declarada.cps", "semantic", "scope"),
    ("invalidos/SCP-02-redeclaracion.cps", "semantic", "scope"),
    ("invalidos/SCP-03-fuera-de-alcance.cps", "semantic", "scope"),
    ("invalidos/SCP-04-fuga-de-bloque.cps", "semantic", "scope"),
    ("invalidos/FUN-01-argumentos-incorrectos.cps", "semantic", "function"),
    ("invalidos/FUN-02-retorno-incompatible.cps", "semantic", "function"),
    ("invalidos/FUN-03-llamada-no-funcion.cps", "semantic", "function"),
    ("invalidos/FUN-04-captura-inexistente.cps", "semantic", "scope"),
    ("invalidos/FUN-05-funcion-duplicada.cps", "semantic", "function"),
    ("invalidos/CTL-01-if-no-booleano.cps", "semantic", "control_flow"),
    ("invalidos/CTL-01-while-no-booleano.cps", "semantic", "control_flow"),
    ("invalidos/CTL-01-do-while-no-booleano.cps", "semantic", "control_flow"),
    ("invalidos/CTL-01-for-no-booleano.cps", "semantic", "control_flow"),
    ("invalidos/CTL-01-switch-no-booleano.cps", "semantic", "control_flow"),
    ("invalidos/CTL-02-break-fuera-de-bucle.cps", "semantic", "control_flow"),
    ("invalidos/CTL-02-continue-fuera-de-bucle.cps", "semantic", "control_flow"),
    ("invalidos/CTL-03-return-global.cps", "semantic", "control_flow"),
    ("invalidos/CTL-04-catch-fuera-de-alcance.cps", "semantic", "scope"),
    ("invalidos/CLS-01-miembro-inexistente.cps", "semantic", "class"),
    ("invalidos/CLS-02-constructor-incorrecto.cps", "semantic", "function"),
    ("invalidos/CLS-03-this-fuera-de-clase.cps", "semantic", "class"),
    ("invalidos/CLS-04-superclase-desconocida.cps", "semantic", "class"),
    ("invalidos/LST-01-lista-heterogenea.cps", "semantic", "array"),
    ("invalidos/LST-02-indice-no-entero.cps", "semantic", "array"),
    ("invalidos/GEN-02-operacion-sin-sentido.cps", "semantic", "type"),
    ("invalidos/GEN-03-variable-duplicada.cps", "semantic", "scope"),
    ("invalidos/GEN-03-parametro-duplicado.cps", "semantic", "function"),
    ("invalidos/EXT-01-foreach-no-arreglo.cps", "semantic", "array"),
    ("invalidos/EXT-02-constructor-implicito-con-argumentos.cps", "semantic", "function"),
    ("invalidos/EXT-03-concatenacion-mixta.cps", "semantic", "type"),
    ("invalidos/EXT-04-null-en-primitivo.cps", "semantic", "type"),
)

WARNING_PROGRAMS = (
    ("advertencias/GEN-01-codigo-inalcanzable.cps", "return", 1),
    (
        "advertencias/GEN-01-codigo-inalcanzable-despues-de-break.cps",
        "break",
        1,
    ),
    (
        "advertencias/GEN-01-codigo-inalcanzable-despues-de-continue.cps",
        "continue",
        1,
    ),
    (
        "advertencias/GEN-01-multiples-instrucciones-inalcanzables.cps",
        "return",
        2,
    ),
)


def compile_program(relative_path: str):
    """Compile one real fixture through the same adapter used by the IDE."""
    path = CPS_ROOT / relative_path
    assert path.is_file(), f"falta el programa demostrativo {relative_path}"
    return analyze_semantics_with_g4(
        GRAMMAR,
        path.read_text(encoding="utf-8"),
        PROFILE,
        "program",
        path,
    )


@pytest.mark.parametrize("relative_path", VALID_PROGRAMS, ids=VALID_PROGRAMS)
def test_valid_cps_demonstrations_are_accepted(relative_path: str) -> None:
    """Every valid fixture must compile without semantic diagnostics."""
    result = compile_program(relative_path)

    assert result.syntax_result.accepted, result.syntax_result.diagnostics
    assert result.semantic_result is not None
    assert result.accepted, result.semantic_result.diagnostics
    assert not result.semantic_result.diagnostics


@pytest.mark.parametrize(
    ("relative_path", "stage", "category"),
    ERROR_PROGRAMS,
    ids=[item[0] for item in ERROR_PROGRAMS],
)
def test_invalid_cps_demonstrations_are_rejected(
    relative_path: str,
    stage: str,
    category: str | None,
) -> None:
    """Every invalid fixture must fail in its isolated diagnostic family."""
    result = compile_program(relative_path)

    if stage == "syntax":
        assert not result.syntax_result.accepted
        assert result.semantic_result is None
        return

    assert result.syntax_result.accepted, result.syntax_result.diagnostics
    assert result.semantic_result is not None
    assert not result.accepted
    error_categories = {
        diagnostic.category.value
        for diagnostic in result.semantic_result.diagnostics
        if diagnostic.severity.value == "error"
    }
    assert error_categories == {category}


@pytest.mark.parametrize(
    ("relative_path", "transfer", "expected_warning_count"),
    WARNING_PROGRAMS,
    ids=[item[0] for item in WARNING_PROGRAMS],
)
def test_warning_cps_demonstrations_are_accepted_and_reported(
    relative_path: str,
    transfer: str,
    expected_warning_count: int,
) -> None:
    """Los programas se aceptan y reportan cada instruccion inalcanzable."""
    result = compile_program(relative_path)

    assert result.accepted
    assert result.semantic_result is not None
    warnings = [
        diagnostic
        for diagnostic in result.semantic_result.diagnostics
        if diagnostic.severity.value == "warning"
    ]
    assert len(warnings) == expected_warning_count
    assert {diagnostic.category.value for diagnostic in warnings} == {"general"}
    assert all(
        diagnostic.message == f"unreachable instruction after {transfer}"
        for diagnostic in warnings
    )


def test_every_cps_demonstration_is_executed_by_this_suite() -> None:
    """Adding an unregistered CPS file must fail the executable inventory."""
    registered = (
        set(VALID_PROGRAMS)
        | {item[0] for item in ERROR_PROGRAMS}
        | {item[0] for item in WARNING_PROGRAMS}
        | {"demostracion-invalida.cps"}
    )
    discovered = {
        path.relative_to(CPS_ROOT).as_posix()
        for path in CPS_ROOT.rglob("*.cps")
    }

    assert discovered == registered


def test_scp_04_demonstration_preserves_every_required_scope_kind() -> None:
    """Flattening semantic scopes must break the SCP-04 evidence."""
    result = compile_program("validos/SCP-04-entornos.cps")

    assert result.accepted
    assert result.semantic_result is not None
    scope_kinds = {
        scope.kind for scope in result.semantic_result.symbol_table.iter_scopes()
    }
    assert {
        ScopeKind.GLOBAL,
        ScopeKind.FUNCTION,
        ScopeKind.CLASS,
        ScopeKind.BLOCK,
    } <= scope_kinds


def test_invalid_delivery_demonstration_reports_all_main_categories() -> None:
    """Dropping a diagnostic family must reduce the mixed demo's evidence."""
    result = compile_program("demostracion-invalida.cps")

    assert result.syntax_result.accepted, result.syntax_result.diagnostics
    assert result.semantic_result is not None
    assert not result.accepted
    categories = {
        diagnostic.category.value
        for diagnostic in result.semantic_result.diagnostics
    }
    assert {
        "type",
        "scope",
        "function",
        "control_flow",
        "class",
        "array",
    } <= categories

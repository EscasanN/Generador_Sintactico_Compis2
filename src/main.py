"""Punto de entrada de la GUI y la CLI de Compiscript.

Uso:
    python -m src.main
    python -m src.main --cps programa.cps
    python -m src.main --cps programa.cps --syntax-only
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GRAMMAR_PATH = REPOSITORY_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
PROFILE_PATH = REPOSITORY_ROOT / "semantic_profiles" / "compiscript.semantic.json"
START_RULE = "program"


def main() -> None:
    """Abre la GUI o ejecuta el análisis solicitado desde la terminal."""
    if len(sys.argv) > 1 and sys.argv[1] == "--cps":
        raise SystemExit(_run_cps_cli(sys.argv[2:]))
    if len(sys.argv) > 1:
        print(
            "Uso: python -m src.main [--cps programa.cps [--syntax-only]]",
            file=sys.stderr,
        )
        raise SystemExit(2)

    from src.gui.app import launch_gui

    launch_gui()


def _run_cps_cli(arguments: Sequence[str]) -> int:
    """Analiza un programa con la gramática oficial de Compiscript."""
    from src.antlr_mode.grammar_info import GrammarInfoError
    from src.antlr_mode.runner import AntlrModeError, analyze_with_g4
    from src.semantic.antlr_adapter import (
        SemanticAdapterError,
        analyze_semantics_with_g4,
    )

    parser = argparse.ArgumentParser(
        prog="python -m src.main --cps",
        description="Analiza sintáctica y semánticamente un programa Compiscript.",
    )
    parser.add_argument("source", help="archivo fuente .cps")
    parser.add_argument(
        "--syntax-only",
        action="store_true",
        help="ejecuta únicamente lexer y parser de ANTLR",
    )
    options = parser.parse_args(list(arguments))
    source_path = Path(options.source)

    try:
        source = source_path.read_text(encoding="utf-8")
        if options.syntax_only:
            syntax_result = analyze_with_g4(GRAMMAR_PATH, source, START_RULE)
            _print_syntax_diagnostics(syntax_result.diagnostics)
            status = "ACCEPT" if syntax_result.accepted else "REJECT"
            print(f"{status} — análisis sintáctico de Compiscript")
            return 0 if syntax_result.accepted else 1

        run = analyze_semantics_with_g4(
            GRAMMAR_PATH,
            source,
            PROFILE_PATH,
            START_RULE,
            source_path,
        )
        _print_syntax_diagnostics(run.syntax_result.diagnostics)
        if run.semantic_result is not None:
            _print_semantic_diagnostics(run.semantic_result.diagnostics)
            _print_symbol_table(run.semantic_result.symbol_table)
        status = "ACCEPT" if run.accepted else "REJECT"
        print(f"{status} — análisis sintáctico y semántico de Compiscript")
        return 0 if run.accepted else 1
    except (OSError, UnicodeError) as exc:
        print(f"ERROR — no se pudo leer el programa: {exc}", file=sys.stderr)
        return 2
    except (AntlrModeError, GrammarInfoError, SemanticAdapterError) as exc:
        print(f"ERROR — {exc}", file=sys.stderr)
        return 2


def _print_syntax_diagnostics(diagnostics: Sequence[object]) -> None:
    for diagnostic in diagnostics:
        print(
            f"[{diagnostic.severity}][{diagnostic.stage}] "
            f"{diagnostic.line}:{diagnostic.column} {diagnostic.message}"
        )


def _print_semantic_diagnostics(diagnostics: Sequence[object]) -> None:
    for diagnostic in diagnostics:
        print(
            f"[{diagnostic.severity.value.upper()}][{diagnostic.category.value}] "
            f"{diagnostic.location.line}:{diagnostic.location.column} "
            f"{diagnostic.message}"
        )


def _print_symbol_table(symbol_table: object) -> None:
    print("Tabla de símbolos:")
    for scope in symbol_table.iter_scopes():
        print(f"  [{scope.kind.value}] {scope.name}")
        for symbol in scope.symbols:
            print(f"    {symbol.kind.value} {symbol.name}: {symbol.type}")


if __name__ == "__main__":
    main()

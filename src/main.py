"""Punto de entrada de la GUI y la CLI de Compiscript.

Uso:
    python -m src.main
    python -m src.main --cps programa.cps
    python -m src.main --cps programa.cps --emit-tac
    python -m src.main --cps programa.cps --emit-tac salida.tac
    python -m src.main --cps programa.cps --show-layout
    python -m src.main --cps programa.cps --syntax-only

Códigos de salida de ``--cps``:
    0  compilación aceptada (TAC verificado por IRVerifier);
    1  rechazo léxico, sintáctico, semántico o de generación de código;
    2  error de lectura/escritura, configuración o dependencia.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GRAMMAR_PATH = REPOSITORY_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
PROFILE_PATH = REPOSITORY_ROOT / "semantic_profiles" / "compiscript.semantic.json"
START_RULE = "program"

USAGE = (
    "Uso: python -m src.main [--cps programa.cps "
    "[--emit-tac [salida.tac]] [--show-layout] [--syntax-only]]"
)
_EMIT_TO_STDOUT = "-"


def main() -> None:
    """Abre la GUI o ejecuta la compilación solicitada desde la terminal."""
    if len(sys.argv) > 1 and sys.argv[1] == "--cps":
        _use_utf8_output()
        raise SystemExit(_run_cps_cli(sys.argv[2:]))
    if len(sys.argv) > 1:
        print(USAGE, file=sys.stderr)
        raise SystemExit(2)

    from src.gui.app import launch_gui

    launch_gui()


def _use_utf8_output() -> None:
    """Evita que la consola de Windows (cp1252) corrompa acentos o el TAC redirigido."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def tac_document(tac: str) -> str:
    """El TAC tal como se imprime o se guarda: siempre termina en salto de línea."""
    return tac if not tac or tac.endswith("\n") else f"{tac}\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.main --cps",
        description=(
            "Compila un programa Compiscript: análisis sintáctico, semántico y "
            "generación de código de tres direcciones (TAC)."
        ),
    )
    parser.add_argument("source", help="archivo fuente .cps")
    parser.add_argument(
        "--emit-tac",
        nargs="?",
        const=_EMIT_TO_STDOUT,
        default=None,
        metavar="RUTA",
        help=(
            "sin RUTA imprime solo el TAC en la salida estándar (diagnósticos en "
            "stderr); con RUTA lo guarda en UTF-8"
        ),
    )
    parser.add_argument(
        "--show-layout",
        action="store_true",
        help="muestra la tabla de símbolos extendida y los registros de activación",
    )
    parser.add_argument(
        "--syntax-only",
        action="store_true",
        help="ejecuta únicamente lexer y parser de ANTLR",
    )
    return parser


def _run_cps_cli(arguments: Sequence[str]) -> int:
    """Compila un programa con la gramática y el perfil oficiales de Compiscript."""
    from src.antlr_mode.grammar_info import GrammarInfoError
    from src.antlr_mode.runner import AntlrModeError, analyze_with_g4
    from src.semantic.antlr_adapter import SemanticAdapterError

    parser = _build_parser()
    try:
        options = parser.parse_args(list(arguments))
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    if options.syntax_only and (options.emit_tac is not None or options.show_layout):
        print(
            "ERROR — --syntax-only no genera TAC ni tabla extendida",
            file=sys.stderr,
        )
        return 2
    source_path = Path(options.source)

    try:
        source = source_path.read_text(encoding="utf-8")
        if options.syntax_only:
            syntax_result = analyze_with_g4(GRAMMAR_PATH, source, START_RULE)
            _print_syntax_diagnostics(syntax_result.diagnostics)
            status = "ACCEPT" if syntax_result.accepted else "REJECT"
            print(f"{status} — análisis sintáctico de Compiscript")
            return 0 if syntax_result.accepted else 1

        from src.codegen.pipeline import compile_compiscript

        result = compile_compiscript(
            source,
            source_path,
            grammar_path=GRAMMAR_PATH,
            profile_path=PROFILE_PATH,
        )
    except (OSError, UnicodeError) as exc:
        print(f"ERROR — no se pudo leer el programa: {exc}", file=sys.stderr)
        return 2
    except (AntlrModeError, GrammarInfoError, SemanticAdapterError) as exc:
        print(f"ERROR — {exc}", file=sys.stderr)
        return 2

    if options.emit_tac == _EMIT_TO_STDOUT:
        # El TAC queda solo en stdout para poder redirigirlo a un archivo.
        _print_report(result, sys.stderr, show_symbols=False, show_layout=options.show_layout)
        if result.accepted:
            sys.stdout.write(tac_document(result.tac))
        return 0 if result.accepted else 1

    _print_report(result, sys.stdout, show_symbols=True, show_layout=options.show_layout)
    if options.emit_tac is not None and result.accepted:
        target = Path(options.emit_tac)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            # LF explícito: el archivo es idéntico en Windows y en Linux.
            target.write_text(tac_document(result.tac), encoding="utf-8", newline="\n")
        except OSError as exc:
            print(f"ERROR — no se pudo guardar el TAC: {exc}", file=sys.stderr)
            return 2
        print(f"TAC guardado en: {target}")
    return 0 if result.accepted else 1


# ---------------------------------------------------------------------- report


def _print_report(
    result: object,
    stream: TextIO,
    *,
    show_symbols: bool,
    show_layout: bool,
) -> None:
    """Diagnósticos de cada fase, tablas opcionales y la línea de estado final."""
    _print_syntax_diagnostics(result.syntax_result.diagnostics, stream)
    semantic_result = result.semantic_result
    if semantic_result is not None:
        _print_semantic_diagnostics(semantic_result.diagnostics, stream)
    intermediate = result.intermediate_result
    if intermediate is not None:
        _print_codegen_diagnostics(intermediate.diagnostics, stream)
    if show_symbols and semantic_result is not None:
        _print_symbol_table(semantic_result.symbol_table, stream)
    if result.accepted:
        if show_layout:
            _print_extended_table(intermediate.symbol_layouts.rows(), stream)
            _print_activation_records(intermediate.activation_records, stream)
        _print_statistics(intermediate.statistics, stream)
        print("ACCEPT — análisis sintáctico, semántico y generación de TAC de Compiscript", file=stream)
        return
    stage = _STAGE_NAMES.get(result.failed_stage, result.failed_stage)
    print(f"REJECT — la compilación se detuvo en la fase {stage}; no se generó TAC", file=stream)


_STAGE_NAMES = {
    "syntax": "sintáctica",
    "semantic": "semántica",
    "codegen": "de generación de código",
}


def _print_syntax_diagnostics(
    diagnostics: Sequence[object], stream: TextIO | None = None
) -> None:
    for diagnostic in diagnostics:
        print(
            f"[{diagnostic.severity}][{diagnostic.stage}] "
            f"{diagnostic.line}:{diagnostic.column} {diagnostic.message}",
            file=stream or sys.stdout,
        )


def _print_semantic_diagnostics(
    diagnostics: Sequence[object], stream: TextIO | None = None
) -> None:
    for diagnostic in diagnostics:
        print(
            f"[{diagnostic.severity.value.upper()}][{diagnostic.category.value}] "
            f"{diagnostic.location.line}:{diagnostic.location.column} "
            f"{diagnostic.message}",
            file=stream or sys.stdout,
        )


def _print_codegen_diagnostics(diagnostics: Sequence[object], stream: TextIO) -> None:
    for diagnostic in diagnostics:
        location = diagnostic.location
        position = f"{location.line}:{location.column}" if location is not None else "-:-"
        print(f"[ERROR][codegen] {position} {diagnostic.code}: {diagnostic.message}", file=stream)


def _print_symbol_table(symbol_table: object, stream: TextIO | None = None) -> None:
    stream = stream or sys.stdout
    print("Tabla de símbolos:", file=stream)
    for scope in symbol_table.iter_scopes():
        print(f"  [{scope.kind.value}] {scope.name}", file=stream)
        for symbol in scope.symbols:
            print(f"    {symbol.kind.value} {symbol.name}: {symbol.type}", file=stream)


EXTENDED_COLUMNS = (
    ("name", "Nombre"),
    ("kind", "Clase"),
    ("type", "Tipo"),
    ("storage", "Almacenamiento"),
    ("offset", "Offset"),
    ("size", "Tamaño"),
    ("label", "Etiqueta"),
    ("level", "Nivel"),
    ("frame", "Frame"),
    ("env_offset", "Env"),
)


def _cell(value: object) -> str:
    return "-" if value is None else str(value)


def _print_extended_table(rows: Sequence[dict[str, object]], stream: TextIO) -> None:
    print("Tabla de símbolos extendida:", file=stream)
    table = [[title for _, title in EXTENDED_COLUMNS]]
    table += [[_cell(row[key]) for key, _ in EXTENDED_COLUMNS] for row in rows]
    widths = [max(len(line[index]) for line in table) for index in range(len(table[0]))]
    for line in table:
        print("  " + "  ".join(text.ljust(width) for text, width in zip(line, widths)).rstrip(),
              file=stream)


def _print_activation_records(frames: Sequence[object], stream: TextIO) -> None:
    print("Registros de activación:", file=stream)
    for frame in frames:
        print(
            f"  {frame.label} ({frame.name}) — nivel {frame.level}, tamaño {frame.size} bytes",
            file=stream,
        )
        for slot in frame.slots:
            kind = "hidden" if slot.hidden else slot.kind.value
            type_text = f" : {slot.type}" if slot.type is not None else ""
            print(
                f"    [{slot.offset:>4}..{slot.end:>4}) {kind:<10} {slot.name}{type_text}",
                file=stream,
            )
        for capture in frame.captures:
            print(
                f"    captura {capture.symbol.name}: dueño {capture.owner_frame}, "
                f"distancia {capture.depth}, offset en entorno {capture.env_offset}",
                file=stream,
            )
        if frame.environment is not None:
            names = ", ".join(
                f"{slot.symbol.name}@{slot.offset}" for slot in frame.environment.slots
            )
            print(
                f"    entorno: {frame.environment.size} bytes, enlace de acceso en "
                f"{frame.environment.parent_offset} [{names}]",
                file=stream,
            )


def _print_statistics(statistics: object, stream: TextIO) -> None:
    print(
        "Estadísticas TAC: "
        f"{statistics['instructions']} instrucciones, "
        f"{statistics['procedures']} procedimientos, "
        f"{statistics['temporaries_created']} temporales creados, "
        f"pico de {statistics['temporary_peak']} temporales vivos",
        file=stream,
    )


if __name__ == "__main__":
    main()

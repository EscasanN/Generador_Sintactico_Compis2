"""
main.py — Generador Sintáctico (YAPar IDE)

Uso:
    python src/main.py                               # GUI
    python src/main.py --cli <yal> <yapar> <input>   # CLI
    python src/main.py --lex <archivo.yal>           # Solo pipeline léxico (modo anterior)
    python src/main.py --cps <programa.cps>           # Compiscript completo
"""
import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == '--lex':
        _run_lex()
    elif len(sys.argv) > 1 and sys.argv[1] == '--cli':
        _run_cli()
    elif len(sys.argv) > 1 and sys.argv[1] == '--cps':
        sys.exit(_run_cps_cli(sys.argv[2:]))
    else:
        from src.gui.app import launch_gui
        launch_gui()


def _run_lex() -> None:
    """Pipeline léxico original (YALex)."""
    if len(sys.argv) < 3:
        print("Uso: python src/main.py --lex <archivo.yal>")
        sys.exit(1)

    filepath = sys.argv[2]
    print(f"\n>>> Procesando archivo: {filepath}\n")

    from src.lexer.codegen import CodeGenError, generate_lexer
    from src.lexer.dfa import DFAError, build_dfa, minimize_dfa
    from src.lexer.nfa import NFAError, build_nfa
    from src.lexer.regex_parser import ParserError, YALexParser
    from src.lexer.resolver import DefinitionResolver, ResolverError
    from src.lexer.scanner import Scanner, ScannerError
    from src.utils.visualizer import render_resolved_spec, render_automata

    try:
        scanner = Scanner(filepath)
        result = scanner.process()
        print(result.pretty_print())

        parser = YALexParser(result)
        lexer_spec = parser.parse()
        print(lexer_spec.pretty_print())

        resolver = DefinitionResolver(lexer_spec)
        resolved_spec = resolver.resolve()
        print(resolved_spec.pretty_print())

        print("\n>>> Generando imagen del AST...")
        path = render_resolved_spec(resolved_spec, output_dir="output")
        print(f">>> Imagen guardada en: {path}\n")

        print("\n>>> Construyendo NFA...")
        nfa = build_nfa(resolved_spec)

        print("\n>>> Construyendo DFA...")
        dfa = build_dfa(nfa)

        print("\n>>> Minimizando DFA...")
        min_dfa = minimize_dfa(dfa)

        print(f"\n>>> Pipeline: NFA={len(nfa.states)} | DFA={len(dfa.states)} | min={len(min_dfa.states)}")

        auto_paths = render_automata(nfa, dfa, min_dfa, output_dir="output")
        print(f">>> NFA: {auto_paths['nfa']}")
        print(f">>> DFA: {auto_paths['dfa']}")
        print(f">>> DFA min: {auto_paths['min_dfa']}")

        lexer_out = os.path.join("output", "Lexer.java")
        generate_lexer(min_dfa, resolved_spec, output_path=lexer_out)
        print(f">>> Lexer generado: {lexer_out}\n")

    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


def _run_cli() -> None:
    if len(sys.argv) < 5:
        print("Uso: python src/main.py --cli <yalex> <yapar> <input.txt>")
        sys.exit(1)

    yalex, yapar, inp = sys.argv[2], sys.argv[3], sys.argv[4]

    from src.parser.yapar_scanner import YAParScanner, build_grammar
    from src.parser.string_analyzer import StringAnalyzer
    from src.parser.tokenizer_bridge import tokenize_input
    from src.utils.visualizer import render_lr0_automaton

    print(f"\nYALex : {yalex}")
    print(f"YAPar : {yapar}")
    print(f"Input : {inp}\n")

    grammar = build_grammar(YAParScanner(yapar).scan())
    sa = StringAnalyzer(grammar)

    print(f"LR(0) states    : {len(sa.automaton.states)}")
    print(f"SLR(1) conflicts: {sa.slr1_table.conflicts or 'none'}")
    print(f"LALR  conflicts : {sa.lalr_table.conflicts or 'none'}")
    print(f"LL(1)           : {'available' if sa.ll1_table else ('conflict: ' + (sa.ll1_error or '')[:60])}\n")

    img = render_lr0_automaton(sa.automaton, "output/lr0")
    print(f"LR(0) image: {img}\n")

    with open(inp, encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]

    print(f"{'Input':<50} SLR(1)   LALR")
    print("-" * 70)
    for line in lines:
        try:
            toks = tokenize_input(yalex, line)
            r = sa.analyze(toks)
            slr = "ACCEPT" if r.slr1_result.accepted else "REJECT"
            lalr = "ACCEPT" if r.lalr_result.accepted else "REJECT"
        except Exception:
            slr = lalr = "LEX ERR"
        print(f"{line!r:<50} {slr:<8} {lalr}")


def _run_cps_cli(arguments: Sequence[str]) -> int:
    """Analyze one source with bundled defaults or an explicitly supplied G4."""
    from src.antlr_mode.grammar_info import GrammarInfoError
    from src.antlr_mode.runner import AntlrModeError, analyze_with_g4
    from src.semantic.antlr_adapter import (
        SemanticAdapterError,
        analyze_semantics_with_g4,
    )

    parser = argparse.ArgumentParser(
        prog="python -m src.main --cps",
        description="Analiza un archivo con ANTLR y, si hay perfil, semántica.",
    )
    parser.add_argument("source", help="archivo fuente, normalmente .cps")
    parser.add_argument("--grammar", help="gramática combinada .g4")
    parser.add_argument("--profile", help="perfil semántico .semantic.json")
    parser.add_argument("--start", help="regla inicial de la gramática")
    parser.add_argument(
        "--syntax-only",
        action="store_true",
        help="ejecuta únicamente lexer y parser",
    )
    options = parser.parse_args(list(arguments))
    if options.syntax_only and options.profile:
        parser.error("--syntax-only y --profile no pueden usarse juntos")

    repository_root = Path(__file__).resolve().parents[1]
    source_path = Path(options.source)
    grammar_path = Path(options.grammar) if options.grammar else (
        repository_root / "src" / "compiscript" / "grammar" / "Compiscript.g4"
    )
    if options.syntax_only:
        profile_path: Path | None = None
    elif options.profile:
        profile_path = Path(options.profile)
    elif options.grammar:
        profile_path = None
    else:
        profile_path = (
            repository_root
            / "semantic_profiles"
            / "compiscript.semantic.json"
        )

    try:
        source = source_path.read_text(encoding="utf-8")
        if profile_path is None:
            syntax_result = analyze_with_g4(
                grammar_path,
                source,
                options.start,
            )
            _print_syntax_diagnostics(syntax_result.diagnostics)
            status = "ACCEPT" if syntax_result.accepted else "REJECT"
            print(f"{status} — solo sintaxis (sin perfil semántico)")
            return 0 if syntax_result.accepted else 1

        run = analyze_semantics_with_g4(
            grammar_path,
            source,
            profile_path,
            options.start,
            source_path,
        )
        _print_syntax_diagnostics(run.syntax_result.diagnostics)
        if run.semantic_result is not None:
            _print_semantic_diagnostics(run.semantic_result.diagnostics)
            _print_symbol_table(run.semantic_result.symbol_table)
        status = "ACCEPT" if run.accepted else "REJECT"
        print(f"{status} — análisis sintáctico y semántico")
        return 0 if run.accepted else 1
    except (OSError, UnicodeError) as exc:
        print(f"ERROR — no se pudo leer un archivo: {exc}", file=sys.stderr)
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

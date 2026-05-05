"""
main.py — Generador Sintáctico (YAPar IDE)

Uso:
    python src/main.py                               # GUI
    python src/main.py --cli <yal> <yapar> <input>   # CLI
    python src/main.py --lex <archivo.yal>           # Solo pipeline léxico (modo anterior)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == '--lex':
        _run_lex()
    elif len(sys.argv) > 1 and sys.argv[1] == '--cli':
        _run_cli()
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


if __name__ == "__main__":
    main()

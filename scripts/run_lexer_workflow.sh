#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

SPEC_FILE="${1:-$ROOT_DIR/tests/inputs/simple.yal}"
INPUT_FILE="${2:-$ROOT_DIR/tests/inputs/test_input.txt}"
OUTPUT_DIR="${3:-$ROOT_DIR/output}"
JAVA_OUT="$OUTPUT_DIR/Lexer.java"
JSON_OUT="$OUTPUT_DIR/LexerData.json"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "[ERROR] No se encontró el intérprete del venv en $VENV_PYTHON" >&2
    exit 1
fi

if [ ! -f "$SPEC_FILE" ]; then
    echo "[ERROR] No se encontró el archivo .yal: $SPEC_FILE" >&2
    exit 1
fi

if [ ! -f "$INPUT_FILE" ]; then
    echo "[ERROR] No se encontró el archivo de entrada: $INPUT_FILE" >&2
    exit 1
fi

if ! command -v javac >/dev/null 2>&1; then
    echo "[ERROR] 'javac' no está disponible en el PATH" >&2
    exit 1
fi

if ! command -v java >/dev/null 2>&1; then
    echo "[ERROR] 'java' no está disponible en el PATH" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo ">>> Generando lexer desde: $SPEC_FILE"
echo ">>> Usando venv: $VENV_PYTHON"

"$VENV_PYTHON" - "$ROOT_DIR" "$SPEC_FILE" "$JAVA_OUT" <<'PY'
import os
import sys

root_dir, spec_file, java_out = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, root_dir)

from src.lexer.codegen import generate_lexer
from src.lexer.dfa import build_dfa, minimize_dfa
from src.lexer.nfa import build_nfa
from src.lexer.regex_parser import YALexParser
from src.lexer.resolver import DefinitionResolver
from src.lexer.scanner import Scanner

scan = Scanner(spec_file).process()
spec = YALexParser(scan).parse()
resolved = DefinitionResolver(spec).resolve()
nfa = build_nfa(resolved)
dfa = build_dfa(nfa)
min_dfa = minimize_dfa(dfa)
generate_lexer(min_dfa, resolved, output_path=java_out)

print(f"[OK] Lexer generado en: {java_out}")
print(f"[OK] Datos JSON en: {os.path.splitext(java_out)[0]}Data.json")
print(f"[OK] Estados NFA: {len(nfa.states)}")
print(f"[OK] Estados DFA: {len(dfa.states)}")
print(f"[OK] Estados DFA mínimo: {len(min_dfa.states)}")
PY

echo ">>> Compilando lexer Java"
javac "$JAVA_OUT"

echo ">>> Ejecutando lexer con: $INPUT_FILE"
java -cp "$OUTPUT_DIR" Lexer "$INPUT_FILE"

echo
echo ">>> Artefactos generados"
echo "    Java: $JAVA_OUT"
echo "    JSON: $JSON_OUT"
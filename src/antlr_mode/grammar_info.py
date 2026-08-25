"""Small, non-generating inspection helpers for ANTLR grammar files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class GrammarInfoError(ValueError):
    """Raised when the selected file is not a usable ANTLR grammar."""


@dataclass(frozen=True, slots=True)
class GrammarInfo:
    path: Path
    name: str
    kind: str
    parser_rules: tuple[str, ...]

    @property
    def default_start_rule(self) -> str:
        if not self.parser_rules:
            raise GrammarInfoError("La gramática no contiene reglas sintácticas.")
        return self.parser_rules[0]


_GRAMMAR_HEADER = re.compile(
    r"\b(?:(lexer|parser)\s+)?grammar\s+([A-Za-z_][A-Za-z0-9_]*)\s*;"
)
_RULE_CANDIDATE = re.compile(
    r"(?:\A|;|})[ \t\r\n]*([a-z][A-Za-z0-9_]*)\b"
)
_NON_RULE_WORDS = {
    "channels",
    "grammar",
    "import",
    "lexer",
    "mode",
    "options",
    "parser",
    "tokens",
}


def _mask_comments_and_strings(source: str) -> str:
    """Replace comments and quoted literals while preserving offsets/newlines."""

    chars = list(source)
    i = 0
    while i < len(chars):
        if source.startswith("//", i):
            end = source.find("\n", i + 2)
            end = len(source) if end == -1 else end
            for j in range(i, end):
                chars[j] = " "
            i = end
            continue

        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            if end == -1:
                end = len(source) - 2
            for j in range(i, min(end + 2, len(chars))):
                if chars[j] not in "\r\n":
                    chars[j] = " "
            i = end + 2
            continue

        if chars[i] in {"'", '"'}:
            quote = chars[i]
            i += 1
            while i < len(chars):
                if chars[i] == "\\":
                    chars[i] = " "
                    if i + 1 < len(chars) and chars[i + 1] not in "\r\n":
                        chars[i + 1] = " "
                    i += 2
                    continue
                if chars[i] == quote:
                    i += 1
                    break
                if chars[i] not in "\r\n":
                    chars[i] = " "
                i += 1
            continue

        i += 1
    return "".join(chars)


def parse_g4_info(source: str, path: str | Path = "<memory>") -> GrammarInfo:
    masked = _mask_comments_and_strings(source)
    header = _GRAMMAR_HEADER.search(masked)
    if header is None:
        raise GrammarInfoError(
            "No se encontró una declaración 'grammar Nombre;' válida."
        )

    grammar_kind = header.group(1) or "combined"
    grammar_name = header.group(2)
    rules: list[str] = []

    for match in _RULE_CANDIDATE.finditer(masked):
        name = match.group(1)
        if name in _NON_RULE_WORDS:
            continue
        tail = masked[match.end() :]
        colon = tail.find(":")
        semicolon = tail.find(";")
        if colon == -1 or (semicolon != -1 and semicolon < colon):
            continue
        if name not in rules:
            rules.append(name)

    if grammar_kind != "lexer" and not rules:
        raise GrammarInfoError("La gramática no contiene reglas de parser.")

    return GrammarInfo(
        path=Path(path),
        name=grammar_name,
        kind=grammar_kind,
        parser_rules=tuple(rules),
    )


def inspect_g4(path: str | Path) -> GrammarInfo:
    grammar_path = Path(path).resolve()
    if grammar_path.suffix.lower() != ".g4":
        raise GrammarInfoError("El archivo seleccionado debe tener extensión .g4.")
    try:
        source = grammar_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GrammarInfoError(f"No se pudo leer la gramática: {exc}") from exc

    info = parse_g4_info(source, grammar_path)
    if grammar_path.stem != info.name:
        raise GrammarInfoError(
            f"ANTLR requiere que el archivo se llame {info.name}.g4; "
            f"se seleccionó {grammar_path.name}."
        )
    return info

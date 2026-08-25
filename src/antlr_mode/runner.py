"""Generate and execute a combined ANTLR grammar without changing project code."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from src.antlr_mode.grammar_info import GrammarInfo, inspect_g4
from src.parser.parse_tree import ParseTreeNode


ANTLR_VERSION = "4.13.2"
ANTLR_DOWNLOAD_URL = (
    f"https://www.antlr.org/download/antlr-{ANTLR_VERSION}-complete.jar"
)
ANTLR_JAR_SHA256 = (
    "eae2dfa119a64327444672aff63e9ec35a20180dc5b8090b7a6ab85125df4d76"
)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ANTLR_OUTPUT = _REPO_ROOT / "output" / "antlr"
_TOOL_CACHE = _ANTLR_OUTPUT / "tools"
_PARSER_CACHE = _ANTLR_OUTPUT / "generated"


class AntlrModeError(RuntimeError):
    """Base error with a message suitable for the IDE."""


class AntlrToolError(AntlrModeError):
    """ANTLR tool or Java is unavailable."""


class AntlrGenerationError(AntlrModeError):
    """The selected grammar could not generate a Python parser."""


@dataclass(frozen=True, slots=True)
class AntlrDiagnostic:
    stage: str
    line: int
    column: int
    message: str
    severity: str = "ERROR"


@dataclass(frozen=True, slots=True)
class AntlrToken:
    token_type: str
    text: str
    line: int
    column: int


@dataclass(slots=True)
class AntlrAnalysisResult:
    grammar: GrammarInfo
    start_rule: str
    tree: ParseTreeNode | None
    diagnostics: list[AntlrDiagnostic]
    tokens: list[AntlrToken]
    generated_directory: Path

    @property
    def accepted(self) -> bool:
        return not any(d.severity == "ERROR" for d in self.diagnostics)


def _download_antlr_jar(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with urllib.request.urlopen(ANTLR_DOWNLOAD_URL, timeout=45) as response:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix="antlr-", suffix=".tmp",
                dir=target.parent, delete=False
            ) as temp_file:
                temp_path = Path(temp_file.name)
                shutil.copyfileobj(response, temp_file)
        if temp_path.stat().st_size < 1_000_000:
            raise AntlrToolError("La descarga de ANTLR está incompleta.")
        if temp_path.read_bytes()[:2] != b"PK":
            raise AntlrToolError("El archivo descargado no es un JAR válido.")
        downloaded_hash = hashlib.sha256(temp_path.read_bytes()).hexdigest()
        if downloaded_hash != ANTLR_JAR_SHA256:
            raise AntlrToolError(
                "La huella SHA-256 del JAR descargado no coincide con "
                f"ANTLR {ANTLR_VERSION}."
            )
        temp_path.replace(target)
    except (OSError, urllib.error.URLError) as exc:
        raise AntlrToolError(
            "No se encontró ANTLR y no fue posible descargarlo. Instala Java, "
            "conecta el equipo a Internet durante el primer uso o define "
            "ANTLR4_JAR con la ruta de antlr-4.13.2-complete.jar."
        ) from exc
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _resolve_antlr_jar() -> Path:
    configured = os.environ.get("ANTLR4_JAR")
    candidates = [
        Path(configured).expanduser() if configured else None,
        _REPO_ROOT / "tools" / f"antlr-{ANTLR_VERSION}-complete.jar",
        _TOOL_CACHE / f"antlr-{ANTLR_VERSION}-complete.jar",
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            actual_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if actual_hash != ANTLR_JAR_SHA256:
                raise AntlrToolError(
                    f"El JAR {candidate} no corresponde a ANTLR {ANTLR_VERSION} "
                    "o está dañado."
                )
            return candidate.resolve()

    cached = candidates[-1]
    assert cached is not None
    _download_antlr_jar(cached)
    return cached.resolve()


def _generation_key(grammar_path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(f"antlr:{ANTLR_VERSION}\0".encode())
    digest.update(grammar_path.read_bytes())
    return digest.hexdigest()[:16]


def _run_generator(grammar: GrammarInfo) -> tuple[Path, str]:
    if grammar.kind != "combined":
        raise AntlrGenerationError(
            "El modo inicial admite gramáticas combinadas ('grammar Nombre;'). "
            "Las gramáticas lexer/parser separadas todavía no están soportadas."
        )
    java = shutil.which("java")
    if java is None:
        raise AntlrToolError(
            "Java no está instalado o no aparece en PATH; ANTLR lo necesita "
            "para generar el Lexer y Parser."
        )

    cache_key = _generation_key(grammar.path)
    output_dir = _PARSER_CACHE / f"{grammar.name}-{cache_key}"
    lexer_path = output_dir / f"{grammar.name}Lexer.py"
    parser_path = output_dir / f"{grammar.name}Parser.py"
    if lexer_path.is_file() and parser_path.is_file():
        return output_dir, cache_key

    output_dir.mkdir(parents=True, exist_ok=True)
    jar = _resolve_antlr_jar()
    command = [
        java,
        "-jar",
        str(jar),
        "-Dlanguage=Python3",
        "-visitor",
        "-no-listener",
        "-encoding",
        "UTF-8",
        "-o",
        str(output_dir),
        grammar.path.name,
    ]
    creation_flags = (
        subprocess.CREATE_NO_WINDOW
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW")
        else 0
    )
    try:
        completed = subprocess.run(
            command,
            cwd=grammar.path.parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            creationflags=creation_flags,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AntlrToolError(f"No se pudo ejecutar ANTLR: {exc}") from exc

    if completed.returncode != 0 or not lexer_path.is_file() or not parser_path.is_file():
        detail = (completed.stderr or completed.stdout or "sin detalle").strip()
        raise AntlrGenerationError(
            f"ANTLR no pudo generar la gramática {grammar.path.name}:\n{detail}"
        )
    return output_dir, cache_key


def _load_module(path: Path, cache_key: str) -> ModuleType:
    module_name = f"_antlr_dynamic_{cache_key}_{path.stem}"
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AntlrModeError(f"No se pudo cargar el módulo generado {path.name}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _token_name(recognizer, token_type: int) -> str:
    symbolic = getattr(recognizer, "symbolicNames", ())
    literal = getattr(recognizer, "literalNames", ())
    if 0 <= token_type < len(symbolic):
        name = symbolic[token_type]
        if name and name != "<INVALID>":
            return name
    if 0 <= token_type < len(literal):
        name = literal[token_type]
        if name and name != "<INVALID>":
            return name
    return str(token_type)


def _convert_tree(node, parser) -> ParseTreeNode:
    get_rule_index = getattr(node, "getRuleIndex", None)
    if callable(get_rule_index):
        rule_index = get_rule_index()
        if 0 <= rule_index < len(parser.ruleNames):
            label = parser.ruleNames[rule_index]
        else:
            label = type(node).__name__
        children = [
            _convert_tree(node.getChild(i), parser)
            for i in range(node.getChildCount())
        ]
        context_name = type(node).__name__.removesuffix("Context")
        expected_context = label[:1].upper() + label[1:]
        alternative = context_name if context_name != expected_context else None
        start = getattr(node, "start", None)
        stop = getattr(node, "stop", None)
        return ParseTreeNode(
            label,
            children,
            rule_name=label,
            alternative=alternative,
            line=max(int(start.line), 1) if start is not None else None,
            column=max(int(start.column) + 1, 1) if start is not None else None,
            end_line=max(int(stop.line), 1) if stop is not None else None,
            end_column=(
                max(int(stop.column) + len(stop.text or ""), 1)
                if stop is not None
                else None
            ),
        )

    text = node.getText() if hasattr(node, "getText") else str(node)
    token = node.getSymbol() if hasattr(node, "getSymbol") else None
    return ParseTreeNode(
        text,
        token_type=_token_name(parser, token.type) if token is not None else None,
        text=text,
        line=max(int(token.line), 1) if token is not None else None,
        column=max(int(token.column) + 1, 1) if token is not None else None,
        end_line=max(int(token.line), 1) if token is not None else None,
        end_column=(
            max(int(token.column) + len(token.text or ""), 1)
            if token is not None
            else None
        ),
    )


def analyze_with_g4(
    grammar_path: str | Path,
    source: str,
    start_rule: str | None = None,
) -> AntlrAnalysisResult:
    """Generate (or reuse) a parser and analyze one complete source document."""

    try:
        from antlr4 import CommonTokenStream, InputStream, Token
        from antlr4.error.ErrorListener import ErrorListener
    except ImportError as exc:
        raise AntlrToolError(
            "Falta antlr4-python3-runtime. Ejecuta: pip install -r requirements.txt"
        ) from exc

    grammar = inspect_g4(grammar_path)
    selected_rule = start_rule or grammar.default_start_rule
    if selected_rule not in grammar.parser_rules:
        raise AntlrModeError(
            f"La regla inicial '{selected_rule}' no existe. "
            f"Disponibles: {', '.join(grammar.parser_rules)}"
        )

    generated_dir, cache_key = _run_generator(grammar)
    lexer_module = _load_module(
        generated_dir / f"{grammar.name}Lexer.py", cache_key
    )
    parser_module = _load_module(
        generated_dir / f"{grammar.name}Parser.py", cache_key
    )
    lexer_class = getattr(lexer_module, f"{grammar.name}Lexer")
    parser_class = getattr(parser_module, f"{grammar.name}Parser")
    diagnostics: list[AntlrDiagnostic] = []

    class _CollectingListener(ErrorListener):
        def __init__(self, stage: str) -> None:
            super().__init__()
            self.stage = stage

        def syntaxError(
            self, recognizer, offendingSymbol, line, column, msg, exc
        ) -> None:
            diagnostics.append(
                AntlrDiagnostic(
                    stage=self.stage,
                    line=max(int(line), 1),
                    column=max(int(column) + 1, 1),
                    message=str(msg),
                )
            )

    lexer = lexer_class(InputStream(source))
    lexer.removeErrorListeners()
    lexer.addErrorListener(_CollectingListener("LEXER"))
    token_stream = CommonTokenStream(lexer)
    token_stream.fill()
    token_stream.seek(0)

    parser = parser_class(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(_CollectingListener("PARSER"))
    public_tokens = [
        AntlrToken(
            token_type=_token_name(parser, token.type),
            text=token.text or "",
            line=max(int(token.line), 1),
            column=max(int(token.column) + 1, 1),
        )
        for token in token_stream.tokens
        if token.type != Token.EOF
    ]
    start_method = getattr(parser, selected_rule, None)
    if not callable(start_method):
        raise AntlrModeError(
            f"El parser generado no expone la regla inicial '{selected_rule}'."
        )
    antlr_tree = start_method()
    if token_stream.LA(1) != Token.EOF:
        remaining = token_stream.LT(1)
        diagnostics.append(
            AntlrDiagnostic(
                stage="PARSER",
                line=max(int(remaining.line), 1),
                column=max(int(remaining.column) + 1, 1),
                message=(
                    "la regla inicial terminó antes del final de la entrada; "
                    f"token restante: {remaining.text!r}"
                ),
            )
        )
    tree = _convert_tree(antlr_tree, parser) if antlr_tree is not None else None

    return AntlrAnalysisResult(
        grammar=grammar,
        start_rule=selected_rule,
        tree=tree,
        diagnostics=diagnostics,
        tokens=public_tokens,
        generated_directory=generated_dir,
    )

"""Puntos de entrada compartidos: analizar no escribe, ejecutar es explícito."""
from dataclasses import dataclass, field
from .ast import build_ast
from .frontend import parse_sql
from .interpreter import Interpreter
from .models import Diagnostic, SourceLocation, SqlError
from .semantic import SemanticAnalyzer


@dataclass
class AnalysisResult:
    syntax: object
    ast: object = None
    diagnostics: list = field(default_factory=list)
    results: list = field(default_factory=list)

    @property
    def accepted(self):
        return not self.diagnostics


def analyze_sql(source, catalog=None, source_path=None, *, storage=None):
    syntax = parse_sql(source,source_path)
    result = AnalysisResult(syntax,diagnostics=list(syntax.diagnostics))
    if not syntax.accepted: return result
    analyzer = SemanticAnalyzer(catalog if catalog is not None else storage.catalog if storage is not None else {'tables':{},'indexes':{}})
    try:
        result.ast = build_ast(syntax)
        data_current = storage is not None
        for stmt in result.ast.statements:
            analyzer.validate(stmt)
            if data_current:
                Interpreter(storage).preflight(stmt)
            if stmt.kind != 'select':
                data_current = False
    except SqlError as exc:
        result.diagnostics.append(exc.diagnostic)
    return result


def execute_sql(source, storage, source_path=None):
    syntax = parse_sql(source,source_path)
    result = AnalysisResult(syntax,diagnostics=list(syntax.diagnostics))
    if not syntax.accepted: return result
    try:
        result.ast = build_ast(syntax)
    except SqlError as exc:
        result.diagnostics.append(exc.diagnostic)
        return result
    for stmt in result.ast.statements:
        storage.reset_stats()
        try:
            storage.refresh()
            analyzer = SemanticAnalyzer(storage.catalog)
            analyzer.validate(stmt)
            interpreter = Interpreter(storage)
            interpreter.preflight(stmt)
            output = interpreter.execute(stmt,analyzer.catalog)
            output.stats = dict(storage.stats)
            result.results.append(output)
        except SqlError as exc:
            diagnostic = exc.diagnostic
            if diagnostic.stage == 'STORAGE':
                diagnostic = Diagnostic('STORAGE',diagnostic.message,stmt.location,diagnostic.code)
            result.diagnostics.append(diagnostic)
            break
        except OSError as exc:
            result.diagnostics.append(Diagnostic('STORAGE',str(exc),stmt.location))
            break
    return result

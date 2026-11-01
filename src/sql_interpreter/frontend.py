"""Lexer/parser exclusivamente en memoria; generación fuera de esta API."""
from dataclasses import dataclass, field
from antlr4 import CommonTokenStream, InputStream, Token
from antlr4.error.ErrorListener import ErrorListener
from .models import Diagnostic, ParseTreeNode, SourceLocation, SqlToken


@dataclass
class ParseResult:
    tokens: list = field(default_factory=list)
    tree: ParseTreeNode | None = None
    diagnostics: list = field(default_factory=list)
    native_tree: object = field(default=None, repr=False)

    @property
    def accepted(self):
        return not self.diagnostics


def location(token, path=None):
    text = token.text or ''
    lines = text.split('\n')
    return SourceLocation(token.line, token.column + 1, token.line + len(lines) - 1,
                          len(lines[-1]) + 1 if len(lines) > 1 else token.column + len(text) + 1, path)


def parse_sql(source: str, source_path: str | None = None) -> ParseResult:
    from .generated.SQLLexer import SQLLexer
    from .generated.SQLParser import SQLParser
    result = ParseResult()

    class Listener(ErrorListener):
        def __init__(self, stage):
            self.stage = stage

        def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
            result.diagnostics.append(Diagnostic(self.stage, msg, SourceLocation(line, column + 1, source_path=source_path)))

    lexer = SQLLexer(InputStream(source))
    lexer.removeErrorListeners()
    lexer.addErrorListener(Listener('LEXER'))
    stream = CommonTokenStream(lexer)
    stream.fill()
    for token in stream.tokens:
        if token.type != Token.EOF:
            name = SQLParser.symbolicNames[token.type]
            if name == '<INVALID>': name = SQLParser.literalNames[token.type]
            result.tokens.append(SqlToken(name, token.text, location(token, source_path)))
    parser = SQLParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(Listener('PARSER'))
    native = parser.script()

    def convert(node):
        if hasattr(node, 'getRuleIndex'):
            name = parser.ruleNames[node.getRuleIndex()]
            return ParseTreeNode(name, [convert(c) for c in node.children or []], name, location=location(node.start, source_path))
        return ParseTreeNode(node.getText(), text=node.getText(), location=location(node.getSymbol(), source_path))

    result.tree = convert(native)
    result.native_tree = native
    return result

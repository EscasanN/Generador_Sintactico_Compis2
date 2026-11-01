"""Contratos neutrales compartidos por CLI, GUI y núcleo."""
from dataclasses import dataclass, field

MAX_INTEGER = 10 ** 4096 - 1


def bounded_integer(text, at):
    text = text.lstrip('0') or '0'
    if len(text) > 4096:
        raise SqlError('INT excede el límite de 4096 dígitos',at)
    return int(text)


@dataclass(frozen=True)
class SourceLocation:
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None
    source_path: str | None = None


@dataclass(frozen=True)
class Diagnostic:
    stage: str
    message: str
    location: SourceLocation
    code: str = 'SQL_ERROR'


class SqlError(Exception):
    def __init__(self, message, location=None, stage='SEMANTIC'):
        super().__init__(message)
        self.diagnostic = Diagnostic(stage, message, location or SourceLocation(1, 1))


@dataclass
class ParseTreeNode:
    symbol: str
    children: list['ParseTreeNode'] = field(default_factory=list)
    rule_name: str | None = None
    text: str | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class SqlToken:
    token_type: str
    text: str
    location: SourceLocation

"""Located, stable backend errors; no partial assembly is an accepted result."""
from dataclasses import dataclass

from src.semantic.diagnostics import SourceLocation


@dataclass(frozen=True, slots=True)
class MipsDiagnostic:
    code: str
    message: str
    location: SourceLocation | None = None
    phase: str = 'mips'


class MipsError(ValueError):
    def __init__(self, code: str, message: str, location: SourceLocation | None = None) -> None:
        self.diagnostic = MipsDiagnostic(code, message, location)
        super().__init__(f'{code}: {message}')

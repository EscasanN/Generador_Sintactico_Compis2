"""Public contracts independent of future layout/call implementations and Qt."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Mapping, Protocol, Sequence
from types import MappingProxyType

from src.codegen.ir import Instruction, OpCode, Operand
from src.mips.diagnostics import MipsDiagnostic
from src.semantic.symbol_table import Symbol

if TYPE_CHECKING:
    from src.codegen.results import CompilationResult
    from src.mips.emitter import MipsEmitter
    from src.mips.registers import RegisterAllocator
    from src.mips.runtime_base import BaseRuntime


@dataclass(frozen=True, slots=True)
class MachineLocation:
    """Reserved region and access width, relative to a physical base register."""
    base: str
    offset: int
    size: int
    width: int

    def __post_init__(self) -> None:
        if any(type(value) is not int for value in (self.offset, self.size, self.width)):
            raise ValueError('machine offsets, reservations and widths must be integers')
        if self.base not in ('$fp', '$sp', '$gp'):
            raise ValueError('unsupported machine base')
        if self.width not in (1, 4, 8) or self.size < self.width:
            raise ValueError('invalid machine width or reservation')
        if self.offset < 0 or self.offset % self.width:
            raise ValueError('negative or misaligned machine offset')

    @property
    def address(self) -> str:
        return f'{self.offset}({self.base})'


def validate_locations(locations: Sequence[MachineLocation]) -> None:
    for index, left in enumerate(locations):
        for right in locations[index + 1:]:
            if left.base == right.base and max(left.offset, right.offset) < min(
                left.offset + left.size, right.offset + right.size
            ):
                raise ValueError('overlapping machine reservations')


class LocationResolver(Protocol):
    def address_of(self, symbol: Symbol, procedure: str) -> MachineLocation: ...
    def temporary_slot(self, lease: tuple[int, int], procedure: str) -> MachineLocation: ...
    def field_offset(self, owner: object, abstract_offset: int) -> int: ...
    def environment_access(self, owner: object, depth: int, offset: int) -> object: ...


class CallEmitter(Protocol):
    def emit_call(self, instruction: Instruction, pending_parameters: Sequence[Operand],
                  context: EmissionContext) -> None: ...
    def emit_return(self, instruction: Instruction, context: EmissionContext) -> None: ...


class InstructionHandler(Protocol):
    def supports(self, opcode: OpCode) -> bool: ...
    def emit(self, instruction: Instruction, context: EmissionContext) -> None: ...


@dataclass(slots=True)
class EmissionContext:
    emitter: MipsEmitter
    registers: RegisterAllocator
    locations: LocationResolver
    runtime: BaseRuntime
    procedure: str = 'global'


@dataclass(frozen=True, slots=True)
class MipsGenerationResult:
    assembly: str = ''
    diagnostics: tuple[MipsDiagnostic, ...] = ()
    layouts: object | None = None
    statistics: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'diagnostics', tuple(self.diagnostics))
        object.__setattr__(self, 'statistics', MappingProxyType(dict(self.statistics)))
        if self.diagnostics and self.assembly:
            raise ValueError('rejected generation cannot expose assembly')

    @property
    def accepted(self) -> bool:
        return bool(self.assembly) and not self.diagnostics


@dataclass(frozen=True, slots=True)
class MarsConfig:
    jar: Path
    timeout: float = 10.0
    step_limit: int = 1_000_000
    delayed_branching: bool = True
    java: str = 'java'

    def __post_init__(self) -> None:
        object.__setattr__(self, 'jar', Path(self.jar))
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError('timeout must be finite and positive')
        if type(self.step_limit) is not int or self.step_limit <= 0:
            raise ValueError('step limit must be a positive integer')


@dataclass(frozen=True, slots=True)
class MipsCompilationResult:
    frontend: CompilationResult
    mips: MipsGenerationResult | None = None

    def __post_init__(self) -> None:
        if self.mips is not None and not self.frontend.accepted:
            raise ValueError('MIPS requires accepted frontend and TAC')

    @property
    def failed_stage(self) -> str | None:
        if not self.frontend.accepted:
            return self.frontend.failed_stage
        if self.mips is None or not self.mips.accepted:
            return 'mips'
        return None

    @property
    def accepted(self) -> bool:
        return self.failed_stage is None


@dataclass(frozen=True, slots=True)
class MipsExecutionResult:
    status: str
    assembled: bool = False
    stdout: str = ''
    stderr: str = ''
    returncode: int | None = None
    diagnostics: tuple[MipsDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, 'diagnostics', tuple(self.diagnostics))

    @property
    def accepted(self) -> bool:
        return self.status == 'success' and self.assembled and self.returncode == 0

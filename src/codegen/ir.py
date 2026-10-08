"""Immutable, structured three-address code."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.semantic.diagnostics import SourceLocation
from src.semantic.types import Type


class OperandKind(Enum):
    CONSTANT = "constant"
    SYMBOL = "symbol"
    TEMPORARY = "temporary"
    LABEL = "label"
    OFFSET = "offset"


class OpCode(Enum):
    COPY = "COPY"
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    MOD = "MOD"
    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    LE = "LE"
    GT = "GT"
    GE = "GE"
    NEG = "NEG"
    NOT = "NOT"
    CAST = "CAST"
    LABEL = "LABEL"
    GOTO = "GOTO"
    IF_TRUE = "IF_TRUE"
    IF_FALSE = "IF_FALSE"
    PARAM = "PARAM"
    CALL = "CALL"
    CLOSURE_CALL = "CLOSURE_CALL"
    RETURN = "RETURN"
    LIST_NEW = "LIST_NEW"
    LIST_SET = "LIST_SET"
    LIST_GET = "LIST_GET"
    LIST_LEN = "LIST_LEN"
    OBJECT_NEW = "OBJECT_NEW"
    FIELD_SET = "FIELD_SET"
    FIELD_GET = "FIELD_GET"
    METHOD_REF = "METHOD_REF"
    ENV_NEW = "ENV_NEW"
    ENV_SET = "ENV_SET"
    ENV_GET = "ENV_GET"
    CLOSURE = "CLOSURE"
    TRY_BEGIN = "TRY_BEGIN"
    TRY_END = "TRY_END"
    CATCH = "CATCH"
    RELEASE = "RELEASE"


@dataclass(frozen=True, slots=True)
class Operand:
    """A typed immediate, address, temporary, label, or byte offset."""

    kind: OperandKind
    value: object
    type: Type | None = None
    lease: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, OperandKind):
            raise TypeError("operand kind must be OperandKind")
        if self.kind in (OperandKind.CONSTANT, OperandKind.SYMBOL, OperandKind.TEMPORARY):
            if not isinstance(self.type, Type):
                raise TypeError("value operands require a semantic Type")
        if self.kind is OperandKind.CONSTANT and self.value is not None:
            if type(self.value) not in (bool, int, float, str):
                raise TypeError("constant must be a primitive literal or null")
        if self.kind in (OperandKind.TEMPORARY, OperandKind.LABEL):
            if not isinstance(self.value, str) or not self.value:
                raise TypeError("temporary and label names must be nonempty strings")
        if self.kind is OperandKind.TEMPORARY:
            if (
                not isinstance(self.lease, tuple)
                or len(self.lease) != 2
                or any(type(part) is not int or part < 0 for part in self.lease)
            ):
                raise ValueError("temporary requires a valid pool lease")
        if self.kind is OperandKind.OFFSET:
            byte_offset = type(self.value) is int
            lexical_offset = (
                isinstance(self.value, tuple)
                and len(self.value) == 2
                and type(self.value[0]) is int
                and self.value[0] >= 0
                and type(self.value[1]) is int
            )
            if not byte_offset and not lexical_offset:
                raise TypeError("offset must be bytes or a (depth, bytes) pair")
        if self.kind is not OperandKind.TEMPORARY and self.lease is not None:
            raise ValueError("only temporaries have leases")


@dataclass(frozen=True, slots=True)
class Instruction:
    """A quadruple with an optional source location for synthetic operations."""

    opcode: OpCode
    arg1: Operand | None = None
    arg2: Operand | None = None
    result: Operand | None = None
    source_location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.opcode, OpCode):
            raise TypeError("opcode must be OpCode")
        if any(
            value is not None and not isinstance(value, Operand)
            for value in (self.arg1, self.arg2, self.result)
        ):
            raise TypeError("instruction fields must be Operand or None")

    @property
    def quadruple(self) -> tuple[OpCode, Operand | None, Operand | None, Operand | None]:
        return self.opcode, self.arg1, self.arg2, self.result


@dataclass(frozen=True, slots=True)
class IRProcedure:
    label: Operand
    parameters: tuple[Operand, ...]
    instructions: tuple[Instruction, ...]
    temporary_peak: int = 0

    def __post_init__(self) -> None:
        if self.label.kind is not OperandKind.LABEL:
            raise TypeError("procedure label must be a label operand")
        if type(self.temporary_peak) is not int or self.temporary_peak < 0:
            raise ValueError("temporary peak must be a nonnegative integer")
        object.__setattr__(self, "parameters", tuple(self.parameters))
        object.__setattr__(self, "instructions", tuple(self.instructions))


@dataclass(frozen=True, slots=True)
class IRProgram:
    global_code: tuple[Instruction, ...] = ()
    procedures: tuple[IRProcedure, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "global_code", tuple(self.global_code))
        object.__setattr__(self, "procedures", tuple(self.procedures))

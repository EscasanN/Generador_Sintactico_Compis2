"""Controlled emission of immutable intermediate instructions."""

from __future__ import annotations

from collections.abc import Iterable

from src.codegen.ir import IRProcedure, IRProgram, Instruction, OpCode, Operand, OperandKind
from src.codegen.names import LabelFactory, TemporaryPool
from src.semantic.diagnostics import SourceLocation
from src.semantic.types import Type


class IRBuilder:
    """Build global code and one procedure at a time."""

    def __init__(self) -> None:
        self.labels = LabelFactory()
        self.temporaries = TemporaryPool()
        self._global_temporaries = self.temporaries
        self._global: list[Instruction] = []
        self._procedures: list[IRProcedure] = []
        self._current: list[Instruction] | None = None
        self._label: Operand | None = None
        self._parameters: tuple[Operand, ...] = ()
        self._returned: set[Operand] = set()

    def begin_procedure(self, label: Operand, parameters: Iterable[Operand]) -> None:
        if self._current is not None:
            raise RuntimeError("a procedure is already open")
        if label.kind is not OperandKind.LABEL:
            raise TypeError("procedure label must be a label operand")
        if self.temporaries.active_count:
            raise RuntimeError("cannot begin a procedure with active global temporaries")
        self._label = label
        self._parameters = tuple(parameters)
        self._current = []
        self.temporaries = TemporaryPool()
        self._returned.clear()

    def end_procedure(self) -> IRProcedure:
        if self._current is None or self._label is None:
            raise RuntimeError("no procedure is open")
        if any(
            temporary not in self._returned
            for temporary in self.temporaries.active_operands
        ):
            raise RuntimeError("cannot close a procedure with active temporaries")
        procedure = IRProcedure(
            self._label,
            self._parameters,
            tuple(self._current),
            self.temporaries.peak_active,
        )
        self._procedures.append(procedure)
        self._current = None
        self._label = None
        self._parameters = ()
        self._returned.clear()
        self.temporaries = self._global_temporaries
        return procedure

    def emit(
        self,
        opcode: OpCode,
        arg1: Operand | None = None,
        arg2: Operand | None = None,
        result: Operand | None = None,
        location: SourceLocation | None = None,
    ) -> Instruction:
        for operand in (arg1, arg2, result):
            if operand is not None and operand.kind is OperandKind.TEMPORARY:
                self.temporaries.validate(operand)
        instruction = Instruction(opcode, arg1, arg2, result, location)
        (self._global if self._current is None else self._current).append(instruction)
        if opcode is OpCode.RETURN and arg1 is not None:
            if arg1.kind is OperandKind.TEMPORARY:
                self._returned.add(arg1)
        return instruction

    def mark(self, label: Operand, location: SourceLocation | None = None) -> Instruction:
        return self.emit(OpCode.LABEL, result=label, location=location)

    def jump(self, label: Operand, location: SourceLocation | None = None) -> Instruction:
        return self.emit(OpCode.GOTO, result=label, location=location)

    def branch_false(
        self, condition: Operand, label: Operand, location: SourceLocation | None = None
    ) -> Instruction:
        return self.emit(OpCode.IF_FALSE, condition, result=label, location=location)

    def branch_true(
        self, condition: Operand, label: Operand, location: SourceLocation | None = None
    ) -> Instruction:
        return self.emit(OpCode.IF_TRUE, condition, result=label, location=location)

    def temporary(self, type_: Type) -> Operand:
        return self.temporaries.acquire(type_)

    def release(self, temporary: Operand, location: SourceLocation | None = None) -> None:
        self.temporaries.validate(temporary)
        self.emit(OpCode.RELEASE, temporary, location=location)
        self.temporaries.release(temporary)

    def build(self) -> IRProgram:
        if self._current is not None:
            raise RuntimeError("cannot build with an open procedure")
        return IRProgram(tuple(self._global), tuple(self._procedures))

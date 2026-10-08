"""Deterministic human-readable rendering of structured TAC."""

from __future__ import annotations

import json

from src.codegen.contracts import Address
from src.codegen.ir import IRProgram, Instruction, OpCode, Operand, OperandKind


_BINARY = {
    OpCode.ADD: "+", OpCode.SUB: "-", OpCode.MUL: "*", OpCode.DIV: "/",
    OpCode.MOD: "%", OpCode.EQ: "==", OpCode.NE: "!=", OpCode.LT: "<",
    OpCode.LE: "<=", OpCode.GT: ">", OpCode.GE: ">=",
}
_UNARY = {OpCode.NEG: "-", OpCode.NOT: "!"}


def format_operand(operand: Operand) -> str:
    """Render one operand without a process-dependent object representation."""
    if operand.kind is OperandKind.CONSTANT:
        value = operand.value
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, (int, float)):
            return str(value)
        raise TypeError("unsupported constant value")
    if operand.kind is OperandKind.OFFSET:
        if isinstance(operand.value, tuple):
            return f"{operand.value[0]}:{operand.value[1]}"
        return str(operand.value)
    if operand.kind is OperandKind.SYMBOL and isinstance(operand.value, Address):
        return str(operand.value)
    if isinstance(operand.value, str):
        return operand.value
    raise TypeError(f"unsupported {operand.kind.value} value")


def format_instruction(instruction: Instruction) -> str:
    """Render one validated quadruple; RELEASE exposes lifetime metadata."""
    opcode = instruction.opcode
    a = format_operand(instruction.arg1) if instruction.arg1 is not None else ""
    b = format_operand(instruction.arg2) if instruction.arg2 is not None else ""
    r = format_operand(instruction.result) if instruction.result is not None else ""
    if opcode is OpCode.COPY:
        return f"{r} = {a}"
    if opcode in _BINARY:
        return f"{r} = {a} {_BINARY[opcode]} {b}"
    if opcode in _UNARY:
        return f"{r} = {_UNARY[opcode]}{a}"
    if opcode is OpCode.CAST:
        return f"{r} = cast {b} {a}"
    if opcode is OpCode.LABEL:
        return f"{r}:"
    if opcode is OpCode.GOTO:
        return f"goto {r}"
    if opcode is OpCode.IF_TRUE:
        return f"if {a} goto {r}"
    if opcode is OpCode.IF_FALSE:
        return f"ifFalse {a} goto {r}"
    if opcode is OpCode.PARAM:
        return f"param {a}"
    if opcode in (OpCode.CALL, OpCode.CLOSURE_CALL):
        call = "call" if opcode is OpCode.CALL else "closure_call"
        text = f"{call} {a}, {b}"
        return f"{r} = {text}" if instruction.result is not None else text
    if opcode is OpCode.RETURN:
        return f"return {a}".rstrip()
    if opcode is OpCode.RELEASE:
        return f"release {a}"
    if opcode in (OpCode.LIST_NEW, OpCode.LIST_LEN, OpCode.ENV_NEW):
        return f"{r} = {opcode.value.lower()} {a}"
    if opcode in (
        OpCode.LIST_GET, OpCode.FIELD_GET, OpCode.METHOD_REF,
        OpCode.CLOSURE, OpCode.ENV_GET,
    ):
        return f"{r} = {opcode.value.lower()} {a}, {b}"
    if opcode in (OpCode.LIST_SET, OpCode.FIELD_SET, OpCode.ENV_SET):
        return f"{opcode.value.lower()} {a}, {b}, {r}"
    if opcode is OpCode.OBJECT_NEW:
        return f"{r} = object_new {a}, {b}"
    if opcode is OpCode.TRY_BEGIN:
        return f"try_begin {r}"
    if opcode is OpCode.TRY_END:
        return "try_end"
    if opcode is OpCode.CATCH:
        return f"catch {r}"
    raise TypeError(f"unsupported opcode: {opcode}")


def format_program(program: IRProgram) -> str:
    """Format global code and procedures in their stored order."""
    sections = ["global:"]
    sections.extend(f"    {format_instruction(item)}" for item in program.global_code)
    for procedure in program.procedures:
        parameters = ", ".join(format_operand(item) for item in procedure.parameters)
        lines = [f"procedure {format_operand(procedure.label)}({parameters}):"]
        lines.extend(f"    {format_instruction(item)}" for item in procedure.instructions)
        sections.append("\n" + "\n".join(lines))
    return "\n".join(sections)

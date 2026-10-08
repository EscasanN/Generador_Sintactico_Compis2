from dataclasses import FrozenInstanceError

import pytest

from src.codegen.ir import Instruction, OpCode, Operand, OperandKind
from src.semantic.diagnostics import SourceLocation
from src.semantic.types import INTEGER


def test_ir_quadruple_is_typed_and_immutable():
    location = SourceLocation(2, 3)
    left = Operand(OperandKind.CONSTANT, 4, INTEGER)
    target = Operand(OperandKind.TEMPORARY, "t0", INTEGER, (0, 0))
    instruction = Instruction(OpCode.ADD, left, left, target, location)

    assert instruction.quadruple == (OpCode.ADD, left, left, target)
    with pytest.raises(FrozenInstanceError):
        instruction.result = left


def test_ir_rejects_an_arbitrary_opcode():
    with pytest.raises(TypeError):
        Instruction("ADD", None, None, None, SourceLocation(1, 1))


def test_immediates_and_temporaries_require_static_types():
    with pytest.raises(TypeError):
        Operand(OperandKind.CONSTANT, None)
    with pytest.raises(TypeError):
        Operand(OperandKind.TEMPORARY, "t0")
    with pytest.raises(ValueError):
        Operand(OperandKind.TEMPORARY, "t0", INTEGER)
    with pytest.raises(TypeError):
        Operand(OperandKind.CONSTANT, [], INTEGER)


def test_program_snapshots_mutable_input_sequences():
    from src.codegen.ir import IRProcedure, IRProgram

    label = Operand(OperandKind.LABEL, "f")
    source = [Instruction(OpCode.RETURN)]
    procedure = IRProcedure(label, (), source)
    program = IRProgram(source, [procedure])
    source.clear()
    assert len(program.global_code) == 1
    assert len(program.procedures[0].instructions) == 1


def test_formatter_is_stable_and_formats_literals_and_procedures():
    from src.codegen.formatter import format_program
    from src.codegen.ir import IRProcedure, IRProgram
    from src.semantic.types import NULL

    location = SourceLocation(1, 1)
    x = Operand(OperandKind.SYMBOL, "global@x", INTEGER)
    number = Operand(OperandKind.CONSTANT, 3, INTEGER)
    program = IRProgram(
        (Instruction(OpCode.COPY, number, result=x, source_location=location),),
        (IRProcedure(
            Operand(OperandKind.LABEL, "fn"),
            (),
            (Instruction(
                OpCode.RETURN,
                Operand(OperandKind.CONSTANT, None, NULL),
                source_location=location,
            ),),
        ),),
    )
    expected = "global:\n    global@x = 3\n\nprocedure fn():\n    return null"
    assert format_program(program) == expected
    assert format_program(program) == expected


def test_formatter_distinguishes_boolean_and_escaped_string_constants():
    from src.codegen.formatter import format_program
    from src.codegen.ir import IRProgram
    from src.semantic.types import BOOLEAN, STRING

    location = SourceLocation(1, 1)
    program = IRProgram((
        Instruction(
            OpCode.PARAM,
            Operand(OperandKind.CONSTANT, True, BOOLEAN),
            source_location=location,
        ),
        Instruction(
            OpCode.PARAM,
            Operand(OperandKind.CONSTANT, 'a"b', STRING),
            source_location=location,
        ),
    ))
    assert format_program(program) == 'global:\n    param true\n    param "a\\"b"'


def test_formatter_rejects_unstable_arbitrary_object():
    from src.codegen.formatter import format_program
    from src.codegen.ir import IRProgram

    program = IRProgram((Instruction(
        OpCode.PARAM,
        Operand(OperandKind.SYMBOL, object(), INTEGER),
        source_location=SourceLocation(1, 1),
    ),))
    with pytest.raises(TypeError):
        format_program(program)


def test_offset_operand_can_encode_lexical_depth_and_byte_offset():
    from src.codegen.formatter import format_operand

    access = Operand(OperandKind.OFFSET, (2, 16))
    assert format_operand(access) == "2:16"

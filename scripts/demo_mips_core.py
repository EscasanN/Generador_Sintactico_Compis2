"""Executable block-1 handoff: manual TAC, injected slots, MIPS and MARS.

Run from the repository root: py -3.14 -m scripts.demo_mips_core --jar PATH
This is an isolated example, not the future .cps compilation pipeline.
"""
import argparse
import os
from pathlib import Path
import sys

from src.codegen.ir import Instruction, OpCode, Operand, OperandKind
from src.mips.emitter import MipsEmitter
from src.mips.models import EmissionContext, MachineLocation, MarsConfig
from src.mips.registers import RegisterAllocator
from src.mips.runtime_base import BaseRuntime
from src.mips.scalar import ScalarLowerer
from src.mips.simulator import run_mars
from src.semantic.diagnostics import SourceLocation
from src.semantic.types import INTEGER


class ExampleLocations:
    """Three fixed demo slots; block 2 will supply the real frame resolver."""
    def temporary_slot(self, lease: tuple[int, int], procedure: str) -> MachineLocation:
        if procedure != 'global' or lease not in {(0, 0), (0, 1), (0, 2)}:
            raise LookupError('unknown example lease')
        return MachineLocation('$fp', 32 + 8 * lease[1], 8, 4)

    def address_of(self, symbol, procedure: str) -> MachineLocation:
        raise LookupError('example contains only temporaries')

    def field_offset(self, owner, abstract_offset: int) -> int:
        raise LookupError('example contains no objects')

    def environment_access(self, owner, depth: int, offset: int) -> object:
        raise LookupError('example contains no environments')


def build_assembly() -> str:
    """Return executable assembly for (2 + 3) * (7 - 1), using two registers."""
    out, locations = MipsEmitter(), ExampleLocations()
    out.mark('main')
    out.emit('li', '$t8', '-8')
    out.emit('and', '$sp', '$sp', '$t8')
    out.emit('addiu', '$sp', '$sp', '-56')
    out.emit('move', '$fp', '$sp')
    registers = RegisterAllocator(out, locations, gpr_count=2)
    context = EmissionContext(out, registers, locations, BaseRuntime())
    constants = [Operand(OperandKind.CONSTANT, n, INTEGER) for n in (2, 3, 7, 1)]
    values = [Operand(OperandKind.TEMPORARY, f't{i}', INTEGER, (0, i)) for i in range(3)]
    location = SourceLocation(1, 1, source_path='manual-example')
    program = [Instruction(OpCode.ADD, constants[0], constants[1], values[0], location),
               Instruction(OpCode.SUB, constants[2], constants[3], values[1], location),
               Instruction(OpCode.MUL, values[0], values[1], values[2], location)]
    ScalarLowerer().lower(program, context)
    context.runtime.print_value(context, values[2])
    context.runtime.exit(context, 0)
    return out.render()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jar', type=Path, default=os.environ.get('MARS_JAR'))
    parser.add_argument('--output', type=Path)
    options = parser.parse_args()
    if options.jar is None:
        parser.error('provide --jar or MARS_JAR')
    assembly = build_assembly()
    try:
        if options.output is not None:
            options.output.parent.mkdir(parents=True, exist_ok=True)
            options.output.write_text(assembly, encoding='utf-8', newline='\n')
    except OSError as error:
        print(error, file=sys.stderr)
        return 2
    result = run_mars(assembly, MarsConfig(options.jar))
    sys.stdout.write(result.stdout)
    if not result.accepted:
        print(result.stderr or result.diagnostics, file=sys.stderr)
    return 0 if result.accepted else 1 if result.status == 'runtime_error' else 2


if __name__ == '__main__':
    raise SystemExit(main())

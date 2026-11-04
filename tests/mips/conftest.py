"""Manual IR and an isolated resolver: no future ABI implementation required."""
from collections.abc import Iterable

import pytest

from src.codegen.contracts import Address
from src.codegen.ir import Instruction, OpCode, Operand, OperandKind
from src.semantic.diagnostics import SourceLocation
from src.semantic.symbol_table import Symbol, SymbolKind
from src.semantic.types import BOOLEAN, FLOAT, INTEGER


def constant(value, type_=INTEGER):
    return Operand(OperandKind.CONSTANT, value, type_)


def temporary(index, type_=INTEGER, name=None):
    return Operand(OperandKind.TEMPORARY, name or f't{index}', type_, (0, index))


def symbol(name, type_=INTEGER):
    item = Symbol(name, SymbolKind.VARIABLE, type_, True, SourceLocation(1, 1))
    return Operand(OperandKind.SYMBOL, Address(item, 'local', name, scope='global'), type_)


def ins(op, a=None, b=None, result=None):
    return Instruction(op, a, b, result, SourceLocation(1, 1))


class SlotResolver:
    """Conservative unique slots, intentionally not Nadissa's symbol/frame layout."""
    def __init__(self, operands: Iterable[Operand]):
        from src.mips.models import MachineLocation
        self.symbols, self.temporaries = {}, {}
        self.size = 32
        for operand in operands:
            if operand is None or operand.kind not in (OperandKind.SYMBOL, OperandKind.TEMPORARY):
                continue
            width = 8 if operand.type == FLOAT else 1 if operand.type == BOOLEAN else 4
            table = self.symbols if operand.kind is OperandKind.SYMBOL else self.temporaries
            key = id(operand.value.symbol) if operand.kind is OperandKind.SYMBOL else operand.lease
            if key not in table:
                table[key] = MachineLocation('$fp', self.size, 8, width)
                self.size += 8

    def address_of(self, symbol, procedure):
        return self.symbols[id(symbol)]

    def temporary_slot(self, lease, procedure):
        return self.temporaries[lease]

    def field_offset(self, owner, abstract_offset):
        raise NotImplementedError('block 2')

    def environment_access(self, owner, depth, offset):
        raise NotImplementedError('block 2')


@pytest.fixture
def compile_scalar():
    def compile_(instructions, outputs=(), gpr_count=8, fpr_count=5, runtime=None,
                 resolver_factory=SlotResolver):
        from src.mips.emitter import MipsEmitter
        from src.mips.models import EmissionContext
        from src.mips.registers import RegisterAllocator
        from src.mips.runtime_base import BaseRuntime
        from src.mips.scalar import ScalarLowerer
        operands = [v for i in instructions for v in (i.arg1, i.arg2, i.result)] + list(outputs)
        resolver = resolver_factory(operands)
        emitter = MipsEmitter()
        emitter.mark('main')
        emitter.emit('li', '$t8', '-8')
        emitter.emit('and', '$sp', '$sp', '$t8')
        emitter.emit('li', '$t8', str(resolver.size))
        emitter.emit('subu', '$sp', '$sp', '$t8')
        emitter.emit('move', '$fp', '$sp')
        for offset in range(0, resolver.size, 4):
            emitter.emit('sw', '$zero', f'{offset}($fp)')
        registers = RegisterAllocator(emitter, resolver, gpr_count=gpr_count, fpr_count=fpr_count)
        context = EmissionContext(emitter, registers, resolver, runtime or BaseRuntime())
        ScalarLowerer().lower(instructions, context)
        for operand in outputs:
            context.runtime.print_value(context, operand)
        context.runtime.exit(context, 0)
        return emitter.render(), registers
    return compile_


@pytest.fixture
def execute_scalar(compile_scalar, mars):
    def execute(instructions, outputs=(), **options):
        from src.mips.simulator import run_mars
        assembly, registers = compile_scalar(instructions, outputs, **options)
        result = run_mars(assembly, mars)
        assert result.accepted, (result, assembly)
        return result.stdout.splitlines(), registers
    return execute

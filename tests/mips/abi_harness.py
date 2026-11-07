"""Manual typed IR with real frame layouts for the block 2 gates.

Nothing here parses source text or needs the block 3 runtime: statics, hidden
parameters, environments and procedures are declared explicitly, then planned
by the production ``PhysicalLayoutPlan`` and assembled by ``ProgramEmitter``.
"""
from __future__ import annotations

from src.codegen.activation import (
    ActivationRecordBuilder, EnvironmentLayout, EnvironmentSlot, RuntimeLayouts,
)
from src.codegen.contracts import Address
from src.codegen.ir import IRProcedure, IRProgram, Instruction, OpCode as O, Operand, OperandKind
from src.codegen.layout import LayoutBuilder, StorageClass, SymbolLayout, SymbolLayoutTable, layout_of
from src.semantic.diagnostics import SourceLocation
from src.semantic.symbol_table import Symbol, SymbolKind
from src.semantic.types import INTEGER, NULL, UNKNOWN

LOCATION = SourceLocation(1, 1)
NULL_CONSTANT = Operand(OperandKind.CONSTANT, None, NULL)


def const(value, type_=INTEGER):
    return Operand(OperandKind.CONSTANT, value, type_)


def label(name):
    return Operand(OperandKind.LABEL, name)


def offset(value):
    return Operand(OperandKind.OFFSET, value)


class ProcedureBuilder:
    def __init__(self, model: 'Model', name: str, parameters=(), hidden=(), environment=None,
                 bound_environment_offset=None):
        self.model, self.name, self.index = model, name, len(model.units)
        self.instructions: list[Instruction] = []
        self.counter = 0
        self._locals: list[tuple[Symbol, Operand]] = []
        self.hidden: dict[str, Operand] = {}
        self.parameters: dict[str, Operand] = {}
        self.environment, self.bound = environment, bound_environment_offset
        self._order = [*hidden, *[p[0] for p in parameters]]
        self._parameter_specs = parameters
        self._hidden_names = tuple(hidden)
        # Operands need their Address now; offsets are only informative (the
        # physical plan uses symbol identity), so the abstract slots come later.
        for position, hidden_name in enumerate(hidden):
            symbol = Symbol(hidden_name, SymbolKind.PARAMETER, UNKNOWN if hidden_name == 'env'
                            else model.receiver_type, False, LOCATION, {'codegen_hidden': True})
            self.hidden[hidden_name] = Operand(OperandKind.SYMBOL, Address(
                symbol, 'parameter', hidden_name, 32 + 8 * position, name), symbol.type)
        for position, (pname, ptype) in enumerate(parameters):
            symbol = Symbol(pname, SymbolKind.PARAMETER, ptype, True, LOCATION)
            self.parameters[pname] = Operand(OperandKind.SYMBOL, Address(
                symbol, 'parameter', pname, 32 + 8 * (len(hidden) + position), name), ptype)
        model.units.append(self)

    # -- operands -------------------------------------------------------------

    def param(self, name):
        return self.parameters.get(name) or self.hidden[name]

    def local(self, name, type_):
        symbol = Symbol(name, SymbolKind.VARIABLE, type_, True, LOCATION)
        operand = Operand(OperandKind.SYMBOL, Address(symbol, 'local', name, None, self.name), type_)
        self._locals.append((symbol, operand))
        return operand

    def tmp(self, type_=INTEGER):
        number = self.counter
        self.counter += 1
        return Operand(OperandKind.TEMPORARY, f't{number}', type_, (self.index, number))

    # -- instructions ------------------------------------------------------------

    def emit(self, op, a=None, b=None, result=None):
        self.instructions.append(Instruction(op, a, b, result, LOCATION))
        return result

    def release(self, *temporaries):
        for item in temporaries:
            self.emit(O.RELEASE, item)

    def copy(self, source, target):
        return self.emit(O.COPY, source, None, target)

    def binary(self, op, a, b, type_=INTEGER):
        return self.emit(op, a, b, self.tmp(type_))

    def call(self, target, arguments=(), result_type=None, keep=False):
        """PARAM... CALL; releases temporary arguments afterwards unless ``keep``."""
        for argument in arguments:
            self.emit(O.PARAM, argument)
        result = self.tmp(result_type) if result_type is not None else None
        self.emit(O.CALL, label(target), const(len(arguments)), result)
        if not keep:
            self.release(*[a for a in arguments if a.kind is OperandKind.TEMPORARY])
        return result

    def call_indirect(self, callee, arguments=(), result_type=None):
        for argument in arguments:
            self.emit(O.PARAM, argument)
        result = self.tmp(result_type) if result_type is not None else None
        self.emit(O.CLOSURE_CALL, callee, const(len(arguments)), result)
        self.release(*[a for a in arguments if a.kind is OperandKind.TEMPORARY])
        return result

    def show(self, value):
        self.emit(O.PARAM, value)
        self.emit(O.CALL, label('print'), const(1))
        if value.kind is OperandKind.TEMPORARY:
            self.release(value)

    def ret(self, value=None):
        self.emit(O.RETURN, value)

    # -- construction --------------------------------------------------------------

    def frame(self):
        builder = ActivationRecordBuilder(self.name, self.name, 0 if self.name == 'global' else 1,
                                          None)
        builder.reserve_header()
        for hidden_name in self._hidden_names:
            builder.reserve_hidden(hidden_name, UNKNOWN if hidden_name == 'env'
                                   else self.model.receiver_type)
        for pname, _ in self._parameter_specs:
            builder.reserve_parameter(self.parameters[pname].value.symbol)
        for symbol, _ in self._locals:
            builder.reserve_local(symbol)
        builder.reserve_temporaries(self.counter)
        return builder.build(environment=self.environment, needs_env='env' in self._hidden_names), \
            builder.symbol_layouts

    def procedure(self):
        parameters = tuple(self.hidden[n] for n in self._hidden_names) + tuple(
            self.parameters[p[0]] for p in self._parameter_specs)
        return IRProcedure(label(self.name), parameters, tuple(self.instructions), self.counter,
                           self.bound)


class Model:
    receiver_type = UNKNOWN

    def __init__(self):
        self.units: list[ProcedureBuilder] = []
        self._static = LayoutBuilder('statics')
        self._static_layouts: list[SymbolLayout] = []
        self.parents: dict[str, str] = {}
        self.classes: dict[str, object] = {}
        self.global_ = ProcedureBuilder(self, 'global')

    def static(self, name, type_):
        symbol = Symbol(name, SymbolKind.VARIABLE, type_, True, LOCATION)
        position, shape = self._static.allocate_type(name, type_)
        self._static_layouts.append(SymbolLayout(symbol, StorageClass.STATIC, shape.size,
                                                 shape.alignment, offset=position))
        return Operand(OperandKind.SYMBOL, Address(symbol, 'static', name, position, None), type_)

    def procedure(self, name, parameters=(), *, hidden=(), parent=None, environment=None,
                  bound_environment_offset=None):
        built = ProcedureBuilder(self, name, parameters, hidden, environment, bound_environment_offset)
        if parent is not None:
            self.parents[name] = parent
        return built

    @staticmethod
    def environment(owner, slots, parent_offset, size):
        """slots: (name, type, offset); the parent link is stored at ``parent_offset``."""
        cells = []
        for name, type_, position in slots:
            shape = layout_of(type_)
            cells.append(EnvironmentSlot(Symbol(name, SymbolKind.VARIABLE, type_, True, LOCATION),
                                         position, shape.size, shape.alignment))
        return EnvironmentLayout(owner, tuple(cells), parent_offset, size, heap=True)

    def build(self):
        frames, entries = [], list(self._static_layouts)
        global_frame = None
        for unit in self.units:
            frame, symbols = unit.frame()
            entries.extend(symbols)
            if unit is self.global_:
                global_frame = frame
            else:
                frames.append(frame)
        table = SymbolLayoutTable(entries, static_size=self._static.total_size())
        layouts = RuntimeLayouts(table, self.classes, tuple(frames), global_frame, None)
        program = IRProgram(tuple(self.global_.instructions),
                            tuple(u.procedure() for u in self.units if u is not self.global_))
        return program, layouts, dict(self.parents)


def assemble(model: Model, *, runtime=None, gpr_count=8, fpr_count=5, before_global=None,
             after_global=None, extra_handlers=(), loader=None):
    from src.mips.calls import ProgramEmitter
    from src.mips.layout import PhysicalLayoutPlan
    program, layouts, parents = model.build()
    plan = PhysicalLayoutPlan.build(program, layouts, parents=parents)
    emitter = ProgramEmitter(plan, runtime, extra_handlers, gpr_count=gpr_count, fpr_count=fpr_count,
                             loader=loader)
    return emitter.assemble(program, before_global=before_global, after_global=after_global), plan, emitter


def execute(model: Model, mars, **options):
    from src.mips.simulator import run_mars
    assembly, plan, emitter = assemble(model, **options)
    result = run_mars(assembly, mars)
    return result, assembly, plan, emitter


def lines(model: Model, mars, **options):
    result, assembly, _, _ = execute(model, mars, **options)
    assert result.accepted, (result.status, result.stdout, result.stderr[-400:])
    return result.stdout.splitlines()


class CanaryProbe:
    """Raw assembly hooks proving ``$sp``, ``$fp`` and ``$s0``-``$s7`` survive the program."""

    def __init__(self):
        self.labels = {}

    def before(self, context):
        out = context.emitter
        for name in ('sp', 'fp'):
            self.labels[name] = out.label(f'saved_{name}')
            out.define(self.labels[name])
            out.data.extend(['.align 2', f'{self.labels[name]}: .word 0'])
            out.references.add(self.labels[name])
        out.emit('sw', '$sp', f'{self.labels["sp"]}')
        out.emit('sw', '$fp', f'{self.labels["fp"]}')
        for number in range(8):
            out.emit('li', f'$s{number}', str(0x5A5A00 + number))

    def after(self, context):
        out, registers = context.emitter, context.registers
        registers.flush()
        registers.invalidate()
        out.emit('li', '$t9', '1')
        for name, register in (('sp', '$sp'), ('fp', '$fp')):
            out.emit('lw', '$t8', f'{self.labels[name]}')
            out.emit('seq', '$t8', '$t8', register)
            out.emit('and', '$t9', '$t9', '$t8')
        for number in range(8):
            out.emit('li', '$t8', str(0x5A5A00 + number))
            out.emit('seq', '$t8', '$t8', f'$s{number}')
            out.emit('and', '$t9', '$t9', '$t8')
        out.emit('move', '$a0', '$t9')
        out.emit('li', '$v0', '1')
        out.emit('syscall')
        out.emit('li', '$a0', '10')
        out.emit('li', '$v0', '11')
        out.emit('syscall')

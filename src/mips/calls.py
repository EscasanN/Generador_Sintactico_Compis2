"""Call and return sequences of the compiler's own ABI (block 2).

Caller:  PARAM values are copied at once into staging slots of the caller's
         frame (they never depend on a register or a lease that is released
         later); the call reserves ``A = 8 * n`` bytes, copies the package so
         that argument ``i`` sits at ``sp + 8*i`` (hidden parameters first),
         runs ``jal``/``jalr`` and finally releases ``A``.
Callee:  ``sp = sp - F``; ``ra`` and the previous ``fp`` are saved before
         ``fp = sp``; argument ``i`` is read at ``fp + F + 8*i``.  Every
         ``RETURN`` loads ``$v0``/``$f0``, writes the frame's backup slot and
         leaves through a single epilogue that restores ``ra``/``fp``/``sp``.

``$s0``-``$s7`` are never touched.  All values living in registers are written
back and the descriptors invalidated before control leaves the procedure.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence

from src.codegen.ir import IRProgram, Instruction, OpCode, Operand, OperandKind
from src.codegen.verifier import IRVerifier
from src.mips.diagnostics import MipsError
from src.mips.emitter import MipsEmitter
from src.mips.layout import (
    ACCESS_LINK_OFFSET, CONTROL_LINK_OFFSET, GLOBAL_UNIT, RETURN_ADDRESS_OFFSET,
    RETURN_VALUE_OFFSET, SLOT_SIZE, PhysicalFrame, PhysicalLayoutPlan, abi_width, representation,
)
from src.mips.models import EmissionContext, MachineLocation
from src.mips.registers import RegisterAllocator
from src.mips.runtime_base import BaseRuntime
from src.mips.scalar import ScalarLowerer
from src.semantic.types import NULL, UNKNOWN, VOID, FunctionType, Type

CALL_OPCODES = frozenset({OpCode.PARAM, OpCode.CALL, OpCode.CLOSURE_CALL, OpCode.RETURN})
EXTERNALS = frozenset({'print'})
UNROLLED_ZERO_WORDS = 64


class CallingConvention:
    """``CallEmitter`` and ``InstructionHandler`` for the call opcodes."""

    def __init__(self, plan: PhysicalLayoutPlan,
                 loader: Callable[[Operand, EmissionContext], str | None] | None = None) -> None:
        """``loader`` lets block 3 materialize values the allocator cannot (string literals).

        It receives each PARAM operand and returns the register that holds its
        value, or ``None`` to fall back on ``RegisterAllocator.getReg``.
        """
        self.plan = plan
        self.loader = loader
        self._pending: dict[str, list[Operand]] = {}
        self._epilogues: dict[tuple[MipsEmitter, str], str] = {}

    # -- handler protocol ---------------------------------------------------------

    def supports(self, opcode: OpCode) -> bool:
        return opcode in CALL_OPCODES

    def emit(self, instruction: Instruction, context: EmissionContext) -> None:
        try:
            if instruction.opcode is OpCode.PARAM:
                self._param(instruction, context)
            elif instruction.opcode is OpCode.RETURN:
                self.emit_return(instruction, context)
            elif instruction.opcode in (OpCode.CALL, OpCode.CLOSURE_CALL):
                pending, self._pending[context.procedure] = self._pending.get(context.procedure, []), []
                self.emit_call(instruction, pending, context)
            else:
                raise MipsError('MIPS-UNSUPPORTED-OPCODE', instruction.opcode.value)
        except MipsError as error:
            if error.diagnostic.location is None and instruction.source_location is not None:
                raise MipsError(error.diagnostic.code, error.diagnostic.message,
                                instruction.source_location) from error
            raise

    # -- procedure frames ---------------------------------------------------------

    def begin_program(self, context: EmissionContext, static_label: str | None = None) -> None:
        """Entry point: normalize ``sp``, point ``$gp`` at the statics, open the global frame."""
        out = context.emitter
        out.mark('main')
        out.emit('li', '$t8', '-8')
        out.emit('and', '$sp', '$sp', '$t8')
        if static_label is not None:
            out.references.add(static_label)
            out.emit('la', '$gp', static_label)
        self._open_frame(context, self.plan.frame(GLOBAL_UNIT), None)

    def begin_procedure(self, context: EmissionContext) -> None:
        label = context.procedure
        signature = self._signature(label)
        out = context.emitter
        out.mark(self.plan.entry_label(label))
        env_index = signature.hidden.index('env') if 'env' in signature.hidden else None
        self._open_frame(context, self.plan.frame(label), env_index)
        self._pending[label] = []

    def end_procedure(self, context: EmissionContext) -> None:
        label = context.procedure
        if self._pending.get(label):
            raise MipsError('MIPS-CALL-ARITY', f'{label}: PARAM sequence without a call')
        frame, out = self.plan.frame(label), context.emitter
        out.mark(self._epilogue(context))
        out.emit('lw', '$ra', f'{RETURN_ADDRESS_OFFSET}($fp)')
        out.emit('lw', '$t9', f'{CONTROL_LINK_OFFSET}($fp)')
        out.emit('addiu', '$sp', '$fp', str(frame.size))
        out.emit('move', '$fp', '$t9')
        out.emit('jr', '$ra')
        out.emit('nop')

    def _open_frame(self, context: EmissionContext, frame: PhysicalFrame,
                    env_index: int | None) -> None:
        out = context.emitter
        out.emit('addiu', '$sp', '$sp', str(-frame.size))
        out.emit('sw', '$ra', f'{RETURN_ADDRESS_OFFSET}($sp)')
        out.emit('sw', '$fp', f'{CONTROL_LINK_OFFSET}($sp)')
        out.emit('move', '$fp', '$sp')
        words = range(ACCESS_LINK_OFFSET, frame.size, 4)
        if len(words) <= UNROLLED_ZERO_WORDS:
            for offset in words:
                out.emit('sw', '$zero', f'{offset}($fp)')
        else:
            loop = out.label('zero_frame')
            out.emit('addiu', '$t8', '$fp', str(ACCESS_LINK_OFFSET))
            out.emit('addiu', '$t9', '$fp', str(frame.size))
            out.mark(loop)
            out.emit('sw', '$zero', '0($t8)')
            out.emit('addiu', '$t8', '$t8', '4')
            out.branch('bne', loop, '$t8', '$t9')
        if env_index is not None:
            out.emit('lw', '$t8', f'{frame.incoming_offset(env_index)}($fp)')
            out.emit('sw', '$t8', f'{ACCESS_LINK_OFFSET}($fp)')

    def _epilogue(self, context: EmissionContext) -> str:
        key = context.emitter, context.procedure
        if key not in self._epilogues:
            self._epilogues[key] = context.emitter.label('epilogue')
        return self._epilogues[key]

    def _signature(self, label: str):
        try:
            return self.plan.signature(label)
        except LookupError as error:
            raise MipsError('MIPS-MISSING-LAYOUT', str(error)) from error

    # -- PARAM -------------------------------------------------------------------

    def _param(self, instruction: Instruction, context: EmissionContext) -> None:
        operand = instruction.arg1
        if operand is None or operand.type in (VOID, None):
            raise MipsError('MIPS-TYPE', 'PARAM needs a value operand')
        pending = self._pending.setdefault(context.procedure, [])
        frame = self.plan.frame(context.procedure)
        offset = frame.staging_offset(len(pending))
        register = self.loader(operand, context) if self.loader is not None else None
        if register is None:
            register = context.registers.getReg(operand)
        context.emitter.store(register, MachineLocation('$fp', offset, SLOT_SIZE, abi_width(operand.type)))
        pending.append(operand)

    # -- CALL / CLOSURE_CALL -----------------------------------------------------

    def emit_call(self, instruction: Instruction, pending_parameters: Sequence[Operand],
                  context: EmissionContext) -> None:
        pending = tuple(pending_parameters)
        count = instruction.arg2.value if instruction.arg2 is not None else None
        if type(count) is not int or count != len(pending):
            raise MipsError('MIPS-CALL-ARITY',
                            f'call declares {count} arguments but {len(pending)} were staged')
        if instruction.opcode is OpCode.CLOSURE_CALL:
            self._closure_call(instruction, pending, context)
            return
        label = str(instruction.arg1.value)
        if label in EXTERNALS:
            self._external(label, instruction, pending, context)
            return
        try:
            signature = self.plan.signature(label)
        except LookupError:
            raise MipsError('MIPS-UNKNOWN-EXTERNAL', f'call to unknown procedure {label}') from None
        self._check_arguments(label, signature.parameter_types, pending)
        self._check_result(label, signature.returns, instruction.result)
        self._barrier(context)
        out = context.emitter
        self._reserve_package(context, len(pending), 0, '$t8')
        out.branch('jal', self.plan.entry_label(label))
        self._release_package(context, len(pending))
        self._receive(instruction.result, context)

    def _external(self, label: str, instruction: Instruction, pending: tuple[Operand, ...],
                  context: EmissionContext) -> None:
        if len(pending) != 1:
            raise MipsError('MIPS-CALL-ARITY', f'{label} takes exactly one argument')
        if instruction.result is not None:
            raise MipsError('MIPS-CALL-SIGNATURE', f'{label} returns no value')
        context.runtime.print_value(context, pending[0])

    @staticmethod
    def _check_arguments(label: str, expected: Sequence[Type], pending: Sequence[Operand]) -> None:
        if len(expected) != len(pending):
            raise MipsError('MIPS-CALL-ARITY',
                            f'{label} takes {len(expected)} parameters, got {len(pending)}')
        for index, (want, got) in enumerate(zip(expected, pending)):
            if representation(want) != representation(got.type):
                raise MipsError('MIPS-CALL-SIGNATURE',
                                f'argument {index} of {label}: {got.type} is not passed as {want}')

    @staticmethod
    def _check_result(label: str, returns: str | None, result: Operand | None) -> None:
        if result is None or returns is None:
            return
        if returns == 'void':
            raise MipsError('MIPS-CALL-SIGNATURE', f'{label} returns no value to store')
        if representation(result.type) != returns:
            raise MipsError('MIPS-CALL-SIGNATURE',
                            f'{label} returns {returns}; destination is {result.type}')

    @staticmethod
    def _barrier(context: EmissionContext) -> None:
        context.registers.flush()
        context.registers.invalidate()

    def _reserve_package(self, context: EmissionContext, count: int, first: int,
                         scratch: str) -> None:
        """``sp -= 8 * (first + count)``; copy staged argument ``i`` to ``8*(first+i)(sp)``."""
        if first + count:
            context.emitter.emit('addiu', '$sp', '$sp', str(-SLOT_SIZE * (first + count)))
        self._copy_staged(context, count, first, scratch)

    def _copy_staged(self, context: EmissionContext, count: int, first: int, scratch: str) -> None:
        """Raw eight-byte copy: staging slot ``i`` -> ``8*(first+i)(sp)``, type agnostic."""
        out = context.emitter
        frame = self.plan.frame(context.procedure)
        for index in range(count):
            source = frame.staging_offset(index)
            for half in (0, 4):
                out.emit('lw', scratch, f'{source + half}($fp)')
                out.emit('sw', scratch, f'{SLOT_SIZE * (first + index) + half}($sp)')

    @staticmethod
    def _release_package(context: EmissionContext, slots: int) -> None:
        if slots:
            context.emitter.emit('addiu', '$sp', '$sp', str(SLOT_SIZE * slots))

    @staticmethod
    def _receive(result: Operand | None, context: EmissionContext) -> None:
        if result is not None:
            context.registers.write(result, '$f0' if representation(result.type) == 'double' else '$v0')

    def _closure_call(self, instruction: Instruction, pending: tuple[Operand, ...],
                      context: EmissionContext) -> None:
        callee, result = instruction.arg1, instruction.result
        signature = callee.type
        if not isinstance(signature, FunctionType):
            raise MipsError('MIPS-CALL-SIGNATURE', 'indirect calls need a function-typed callee')
        self._check_arguments('closure', signature.parameter_types, pending)
        returns = (None if signature.return_type == UNKNOWN else
                   'void' if signature.return_type == VOID else representation(signature.return_type))
        self._check_result('closure', returns, result)
        out, count = context.emitter, len(pending)
        self._barrier(context)
        if callee.kind is OperandKind.CONSTANT and callee.type != NULL:
            raise MipsError('MIPS-CALL-SIGNATURE', 'constant callee must be null')
        if callee.kind is OperandKind.CONSTANT:
            out.emit('move', '$t8', '$zero')
        else:
            out.load('$t8', context.registers.location(callee))
        ready, masked = out.label('callable_ready'), out.label('callable_mask')
        out.branch('bnez', ready, '$t8')
        context.runtime.error(context, 'NULL_ACCESS')
        out.mark(ready)
        out.emit('lw', '$t9', '24($t8)')
        out.emit('sltiu', '$a2', '$t9', '4')
        out.branch('bnez', masked, '$a2')
        context.runtime.error(context, 'INVALID_CALLABLE')
        out.mark(masked)
        done = out.label('call_done')
        variants = [out.label(f'call_mask_{mask}') for mask in range(4)]
        for mask in range(3):
            out.emit('li', '$a2', str(mask))
            out.branch('beq', variants[mask], '$t9', '$a2')
        out.branch('b', variants[3])  # the only remaining valid mask: this and env
        for mask in range(4):
            out.mark(variants[mask])
            # The runtime mask decides the physical arity: this first, then env.
            hidden = [name for bit, name in ((2, 'this'), (1, 'env')) if mask & bit]
            slots = len(hidden) + count
            if slots:
                out.emit('addiu', '$sp', '$sp', str(-SLOT_SIZE * slots))
            for slot, name in enumerate(hidden):
                out.emit('lw', '$a0', '16($t8)' if name == 'this' else '8($t8)')
                out.emit('sw', '$a0', f'{SLOT_SIZE * slot}($sp)')
                out.emit('sw', '$zero', f'{SLOT_SIZE * slot + 4}($sp)')
            self._copy_staged(context, count, len(hidden), '$a0')
            out.emit('lw', '$t9', '0($t8)')
            out.emit('jalr', '$t9')
            out.emit('nop')
            self._release_package(context, slots)
            if mask != 3:
                out.branch('b', done)
        out.mark(done)
        self._receive(result, context)

    # -- RETURN ------------------------------------------------------------------

    def emit_return(self, instruction: Instruction, context: EmissionContext) -> None:
        label = context.procedure
        if label == GLOBAL_UNIT:
            raise MipsError('MIPS-INVALID-IR', 'return outside a procedure')
        signature = self._signature(label)
        out, registers, value = context.emitter, context.registers, instruction.arg1
        if value is not None:
            if signature.returns != representation(value.type):
                raise MipsError('MIPS-CALL-SIGNATURE', f'{label} returns inconsistent representations')
            register = registers.getReg(value)
            out.emit('mov.d' if signature.returns == 'double' else 'move',
                     '$f0' if signature.returns == 'double' else '$v0', register)
        elif signature.returns == 'double':
            out.emit('l.d', '$f0', out.double(0.0))
        elif signature.returns == 'word':
            out.emit('move', '$v0', '$zero')
        registers.flush()
        registers.invalidate()
        if signature.returns == 'double':
            out.emit('s.d', '$f0', f'{RETURN_VALUE_OFFSET}($fp)')
        elif signature.returns == 'word':
            out.emit('sw', '$v0', f'{RETURN_VALUE_OFFSET}($fp)')
        out.branch('b', self._epilogue(context))


class ProgramEmitter:
    """Reference composition: every opcode has exactly one handler.

    Plans and verifies the whole program first, then emits the entry point, the
    global code and each procedure with its own register descriptors.
    """

    def __init__(self, plan: PhysicalLayoutPlan, runtime: BaseRuntime | None = None,
                 extra_handlers: Sequence[object] = (), *, gpr_count: int = 8,
                 fpr_count: int = 5,
                 loader: Callable[[Operand, EmissionContext], str | None] | None = None) -> None:
        from src.mips.environments import EnvironmentHandler
        self.plan, self.runtime = plan, runtime or BaseRuntime()
        self.calls = CallingConvention(plan, loader)
        self.handlers = [ScalarLowerer(), self.calls, EnvironmentHandler(plan), *extra_handlers]
        self.counts = (gpr_count, fpr_count)
        self.statistics: dict[str, int] = {}
        self.per_procedure: dict[str, dict[str, int]] = {}

    def assemble(self, program: IRProgram, *,
                 before_global: Callable[[EmissionContext], None] | None = None,
                 after_global: Callable[[EmissionContext], None] | None = None) -> str:
        errors = IRVerifier().verify(program)
        if errors:
            raise MipsError('MIPS-INVALID-IR', errors[0].message, errors[0].location)
        emitter = MipsEmitter()
        static_label = None
        if self.plan.static_size:
            static_label = emitter.label('static_area')
            emitter.define(static_label)
            emitter.data.extend(['.align 3', f'{static_label}: .space {self.plan.static_size}'])
        self._unit(emitter, GLOBAL_UNIT, program.global_code,
                   lambda ctx: (self.calls.begin_program(ctx, static_label),
                                before_global(ctx) if before_global else None),
                   lambda ctx: (after_global(ctx) if after_global else None,
                                self.runtime.exit(ctx, 0)))
        for procedure in program.procedures:
            self._unit(emitter, str(procedure.label.value), procedure.instructions,
                       self.calls.begin_procedure, self.calls.end_procedure)
        self.statistics = {
            'instructions': sum(1 for line in emitter.text if line.startswith('    ')),
            'frames': len(self.per_procedure),
            'stack_bytes': sum(v['stack_bytes'] for v in self.per_procedure.values()),
            'spills': sum(v['spills'] for v in self.per_procedure.values()),
            'reloads': sum(v['reloads'] for v in self.per_procedure.values()),
        }
        return emitter.render()

    def _unit(self, emitter: MipsEmitter, name: str, instructions: Sequence[Instruction],
              begin: Callable, end: Callable) -> None:
        registers = RegisterAllocator(emitter, self.plan, name, gpr_count=self.counts[0],
                                      fpr_count=self.counts[1])
        context = EmissionContext(emitter, registers, self.plan, self.runtime, name)
        begin(context)
        for item in instructions:
            self._dispatch(item, context)
        end(context)
        self.per_procedure[name] = {
            'stack_bytes': self.plan.frame(name).size, 'spills': registers.spills,
            'reloads': registers.reloads,
        }

    def _dispatch(self, item: Instruction, context: EmissionContext) -> None:
        matches = [h for h in self.handlers if h.supports(item.opcode)]
        if not matches:
            raise MipsError('MIPS-UNSUPPORTED-OPCODE', item.opcode.value, item.source_location)
        if len(matches) > 1:
            raise MipsError('MIPS-INTERNAL', f'{item.opcode.value} has several handlers',
                            item.source_location)
        if item.source_location is not None:
            context.emitter.source_map[len(context.emitter.text)] = item.source_location
        matches[0].emit(item, context)

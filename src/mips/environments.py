"""Capture environments, closures and bound methods (block 2).

* ``ENV_NEW`` reserves a zeroed environment in the heap through block 1's
  ``BaseRuntime.allocate`` so a closure may outlive the frame that created it.
* ``ENV_GET``/``ENV_SET`` with a ``(depth, offset)`` pair follow the access
  links through *each ancestor's own* ``EnvironmentLayout`` (never a universal
  parent offset and never the control link); a plain byte offset addresses the
  environment pointed to by the operand directly.  Every closure shares the
  cell, so sibling closures observe one another's writes.
* ``CLOSURE`` and ``METHOD_REF`` build a 32-byte callable descriptor:

  ======  ======================================================
  offset  contents
  ======  ======================================================
  0       code address
  8       environment pointer
  16      receiver (``this``)
  24      hidden-parameter mask (bit 0 ``env``, bit 1 ``this``)
  ======  ======================================================

  ``CLOSURE_CALL`` (see ``calls``) reads the mask at run time.
"""
from __future__ import annotations

from src.codegen.ir import Instruction, OpCode, Operand, OperandKind
from src.mips.diagnostics import MipsError
from src.mips.layout import PhysicalLayoutPlan, memory_width, representation
from src.mips.models import EmissionContext
from src.semantic.types import FLOAT, NULL, FunctionType

ENV_OPCODES = frozenset({OpCode.ENV_NEW, OpCode.ENV_SET, OpCode.ENV_GET,
                         OpCode.CLOSURE, OpCode.METHOD_REF})
DESCRIPTOR_SIZE = 32
CODE_OFFSET, ENV_OFFSET, RECEIVER_OFFSET, MASK_OFFSET = 0, 8, 16, 24
MASK_ENV, MASK_THIS = 1, 2


def allocate_descriptor(context: EmissionContext) -> str:
    """Zeroed callable descriptor in the heap; its address is returned in ``$t8``.

    Like ``BaseRuntime.allocate`` it is a register barrier, and the pointer must
    be consumed before another emission that uses the scratch registers.
    """
    return context.runtime.allocate(context, DESCRIPTOR_SIZE)


def fill_descriptor(context: EmissionContext, pointer: str, entry: str, mask: int, *,
                    env: str | None = None, receiver: str | None = None) -> None:
    """Store code, mask and, as the mask demands, the environment and receiver.

    ``env``/``receiver`` are registers already holding the values.  A mask bit
    without its value (or the opposite) is a malformed descriptor.  Uses ``$t9``.
    """
    if type(mask) is not int or mask & ~(MASK_ENV | MASK_THIS):
        raise MipsError('MIPS-INVALID-IR', f'invalid hidden-parameter mask {mask}')
    if bool(mask & MASK_ENV) != (env is not None) or bool(mask & MASK_THIS) != (receiver is not None):
        raise MipsError('MIPS-INVALID-IR', 'descriptor mask and hidden values disagree')
    out = context.emitter
    out.references.add(entry)
    out.emit('la', '$t9', entry)
    out.emit('sw', '$t9', f'{CODE_OFFSET}({pointer})')
    if env is not None:
        out.emit('sw', env, f'{ENV_OFFSET}({pointer})')
    if receiver is not None:
        out.emit('sw', receiver, f'{RECEIVER_OFFSET}({pointer})')
    out.emit('li', '$t9', str(mask))
    out.emit('sw', '$t9', f'{MASK_OFFSET}({pointer})')


class EnvironmentHandler:
    """``InstructionHandler`` for the environment and callable opcodes."""

    def __init__(self, plan: PhysicalLayoutPlan) -> None:
        self.plan = plan

    def supports(self, opcode: OpCode) -> bool:
        return opcode in ENV_OPCODES

    def emit(self, instruction: Instruction, context: EmissionContext) -> None:
        try:
            handler = {
                OpCode.ENV_NEW: self._new, OpCode.ENV_SET: self._set, OpCode.ENV_GET: self._get,
                OpCode.CLOSURE: self._closure, OpCode.METHOD_REF: self._method,
            }.get(instruction.opcode)
            if handler is None:
                raise MipsError('MIPS-UNSUPPORTED-OPCODE', instruction.opcode.value)
            handler(instruction, context)
        except MipsError as error:
            if error.diagnostic.location is None and instruction.source_location is not None:
                raise MipsError(error.diagnostic.code, error.diagnostic.message,
                                instruction.source_location) from error
            raise

    # -- environments -----------------------------------------------------------

    @staticmethod
    def _pointer_result(result: Operand | None) -> None:
        if result is None or result.type == FLOAT or representation(result.type) != 'word':
            raise MipsError('MIPS-TYPE', 'a pointer result must live in an integer register')

    def _new(self, instruction: Instruction, context: EmissionContext) -> None:
        size, result = instruction.arg1, instruction.result
        self._pointer_result(result)
        if size is None or size.kind is not OperandKind.CONSTANT or type(size.value) is not int \
                or size.value <= 0 or size.value % 4:
            raise MipsError('MIPS-INVALID-ADDRESS', 'ENV_NEW needs a positive byte size')
        pointer = context.runtime.allocate(context, size.value)
        context.registers.write(result, pointer)

    def _walk(self, instruction: Instruction, context: EmissionContext, base: str) -> tuple[str, int]:
        """Leave the cell's environment pointer in ``$t8``; return (register, offset)."""
        offset = instruction.arg2
        if offset is None or offset.kind is not OperandKind.OFFSET:
            raise MipsError('MIPS-INVALID-ADDRESS', 'environment access needs an offset operand')
        out = context.emitter
        if type(offset.value) is int:
            links, cell = (), offset.value
            if cell < 0:
                raise MipsError('MIPS-INVALID-ADDRESS', 'negative environment offset')
        else:
            depth, cell = offset.value
            try:
                access = self.plan.environment_access(context.procedure, depth, cell)
            except LookupError as error:
                raise MipsError('MIPS-MISSING-LAYOUT', str(error)) from error
            links, cell = access.links, access.offset
        out.emit('move', '$t8', base)
        for link in links:
            out.emit('lw', '$t8', f'{link}($t8)')
        return '$t8', cell

    @staticmethod
    def _check_cell(type_, cell: int) -> int:
        width = memory_width(type_)
        if cell % width:
            raise MipsError('MIPS-INVALID-ADDRESS', f'offset {cell} is not aligned for {type_}')
        return width

    def _get(self, instruction: Instruction, context: EmissionContext) -> None:
        env, result = instruction.arg1, instruction.result
        registers, out = context.registers, context.emitter
        if env is None or representation(env.type) != 'word' or result is None:
            raise MipsError('MIPS-TYPE', 'ENV_GET needs an environment pointer and a destination')
        base = registers.getReg(env, pinned=True)
        pointer, cell = self._walk(instruction, context, base)
        width = self._check_cell(result.type, cell)
        scratch = '$f14' if result.type == FLOAT else '$t9'
        out.emit({1: 'lbu', 4: 'lw', 8: 'l.d'}[width], scratch, f'{cell}({pointer})')
        registers.unpin(env)
        registers.write(result, scratch)

    def _set(self, instruction: Instruction, context: EmissionContext) -> None:
        env, value = instruction.arg1, instruction.result
        registers, out = context.registers, context.emitter
        if env is None or representation(env.type) != 'word' or value is None:
            raise MipsError('MIPS-TYPE', 'ENV_SET needs an environment pointer and a value')
        base = registers.getReg(env, pinned=True)
        source = registers.getReg(value, pinned=True)
        pointer, cell = self._walk(instruction, context, base)
        width = self._check_cell(value.type, cell)
        out.emit({1: 'sb', 4: 'sw', 8: 's.d'}[width], source, f'{cell}({pointer})')
        registers.unpin(env)
        registers.unpin(value)

    # -- callable descriptors ---------------------------------------------------

    def _signature(self, label_operand: Operand | None):
        if label_operand is None or label_operand.kind is not OperandKind.LABEL:
            raise MipsError('MIPS-INVALID-IR', 'a callable needs a procedure label')
        label = str(label_operand.value)
        try:
            return self.plan.signature(label)
        except LookupError:
            raise MipsError('MIPS-UNKNOWN-EXTERNAL', f'no procedure labelled {label}') from None

    @staticmethod
    def _callable_result(result: Operand | None) -> None:
        if result is None or not isinstance(result.type, FunctionType):
            raise MipsError('MIPS-TYPE', 'a callable must be stored in a function-typed value')

    def _closure(self, instruction: Instruction, context: EmissionContext) -> None:
        signature = self._signature(instruction.arg1)
        env, result = instruction.arg2, instruction.result
        self._callable_result(result)
        if 'this' in signature.hidden:
            raise MipsError('MIPS-INVALID-IR', f'{signature.label} needs a receiver; use METHOD_REF')
        wants_env = 'env' in signature.hidden
        null_env = env is not None and env.kind is OperandKind.CONSTANT and env.value is None
        if env is None or env.type is None or (not null_env and representation(env.type) != 'word'):
            raise MipsError('MIPS-TYPE', 'CLOSURE needs an environment pointer or null')
        if wants_env == null_env:
            raise MipsError('MIPS-INVALID-IR', f'{signature.label} '
                            + ('needs an environment' if wants_env else 'takes no environment'))
        registers = context.registers
        descriptor = allocate_descriptor(context)
        source = registers.getReg(env) if wants_env else None
        fill_descriptor(context, descriptor, self.plan.entry_label(signature.label),
                        signature.mask, env=source)
        registers.write(result, descriptor)

    def _method(self, instruction: Instruction, context: EmissionContext) -> None:
        receiver, result = instruction.arg1, instruction.result
        signature = self._signature(instruction.arg2)
        self._callable_result(result)
        if 'this' not in signature.hidden:
            raise MipsError('MIPS-INVALID-IR', f'{signature.label} is not a method')
        if receiver is None or receiver.type == NULL or representation(receiver.type) != 'word' \
                or receiver.kind is OperandKind.CONSTANT:
            raise MipsError('MIPS-TYPE', 'METHOD_REF needs a receiver reference')
        bound = signature.bound_environment_offset
        if ('env' in signature.hidden) != (bound is not None):
            raise MipsError('MIPS-INVALID-IR', f'{signature.label} has inconsistent bound environment')
        out, registers = context.emitter, context.registers
        descriptor = allocate_descriptor(context)
        source = registers.getReg(receiver)
        ready = out.label('receiver_ready')
        registers.flush()
        out.branch('bnez', ready, source)
        context.runtime.error(context, 'NULL_ACCESS')
        out.mark(ready)
        if bound is not None:
            out.emit('lw', '$a0', f'{bound}({source})')   # the environment the instance captured
        fill_descriptor(context, descriptor, self.plan.entry_label(signature.label),
                        signature.mask, env='$a0' if bound is not None else None, receiver=source)
        registers.write(result, descriptor)

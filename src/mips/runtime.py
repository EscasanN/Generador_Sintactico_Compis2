"""Complete Compiscript runtime: strings, printing, errors and helpers (block 3).

``CompiscriptRuntime`` extends block 1's ``BaseRuntime`` without changing it:

* **Strings** are heap or ``.data`` objects: byte length (UTF-8) at offset 0,
  padding up to 8 and the content from offset 8.  Literals are emitted as
  numeric bytes, so any Unicode text is accepted; ``null`` is address 0 and is
  never the empty string.  ``+`` concatenates into a new object, ``==``/``!=``
  compare contents (``null == null``), ordered operators compare unsigned
  UTF-8 bytes lexicographically.
* **print** dispatches by the operand's type: block 1 handles numbers,
  booleans and ``null``; strings are written with syscall 15 (descriptor 1,
  explicit length) so UTF-8 survives; lists, objects and callables print the
  stable markers ``[list]``, ``[object]`` and ``[function]``.  A null
  reference prints ``null``.
* **Errors**: ``error`` is the non-returning provider of block 1.  It leaves the
  error's payload string in ``$a0`` and jumps to ``raise``, which pops the
  active handler record (see ``exceptions``) and resumes its catch, or prints
  ``RuntimeError: CODE`` and exits with code 1.

Helper routines are leaf procedures of the same ABI with an empty frame:
arguments are 8-byte slots at ``sp + 8*i``, the result comes back in ``$v0``.
They only use ``$a0``-``$a3``, ``$v0``/``$v1``, ``$t8``/``$t9`` and never touch
``$sp``, ``$fp``, ``$s*`` or allocatable registers (``raise`` restores ``$s*``
from the handler record); callers still place a
register barrier before the call.  They are emitted once per program, after
every unit, only when referenced.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.codegen.ir import Instruction, OpCode, Operand
from src.mips.diagnostics import MipsError
from src.mips.emitter import MipsEmitter
from src.mips.exceptions import SAVED_OFFSET
from src.mips.models import EmissionContext, LocationResolver
from src.mips.registers import RegisterAllocator
from src.mips.runtime_base import BaseRuntime
from src.semantic.types import BOOLEAN, NULL, STRING, UNKNOWN, ArrayType, ClassType, FunctionType

STRING_HEADER = 8
ERROR_CODES = frozenset({'DIV_ZERO', 'INDEX_OUT_OF_RANGE', 'NULL_ACCESS', 'INVALID_CALLABLE'})
MARKERS = ((ArrayType, '[list]'), (ClassType, '[object]'), (FunctionType, '[function]'))
HELPERS = ('concat', 'equals', 'compare')
ORDERED = {OpCode.LT: 'slt', OpCode.LE: 'sle', OpCode.GT: 'sgt', OpCode.GE: 'sge'}


@dataclass
class _ProgramState:
    """Per-emitter labels: a runtime may serve several emissions independently."""
    strings: dict[bytes, str] = field(default_factory=dict)
    helpers: dict[str, str] = field(default_factory=dict)
    used: set[str] = field(default_factory=set)
    head: str | None = None
    payload: str | None = None
    raise_label: str | None = None
    emitted: bool = False


def guard(context: EmissionContext, mnemonic: str, operands: tuple[str, ...], code: str) -> None:
    """Continue when ``mnemonic operands`` branches; otherwise raise ``code``.

    Values are flushed first, so both the error path and the success path see
    memory up to date and the register descriptors stay valid afterwards.
    """
    out = context.emitter
    context.registers.flush()
    ok = out.label('guard_ok')
    out.branch(mnemonic, ok, *operands)
    context.runtime.error(context, code)
    out.mark(ok)


class RuntimeRegisterAllocator(RegisterAllocator):
    """Block 1's allocator plus the constant provider for string literals.

    A string literal is the address of its ``.data`` object; the allocator
    otherwise rejects it (``literal requires a runtime provider``).  This also
    resolves string literals passed as ``PARAM`` or stored into lists, fields,
    environments and return values (INC-B2-02) without a separate loader.
    """

    def __init__(self, emitter: MipsEmitter, locations: LocationResolver, procedure: str = 'global',
                 *, runtime: 'CompiscriptRuntime', gpr_count: int = 8, fpr_count: int = 5,
                 saved: tuple[str, ...] = ()) -> None:
        super().__init__(emitter, locations, procedure, gpr_count=gpr_count, fpr_count=fpr_count,
                         saved=saved)
        self.runtime = runtime

    def _constant(self, register: str, value: Operand) -> None:
        if value.type == STRING:
            if value.value is None:
                self.emitter.emit('li', register, '0')
            elif type(value.value) is not str:
                raise MipsError('MIPS-TYPE', 'string literal must be text')
            else:
                self.emitter.emit('la', register, self.runtime.string_literal(self.emitter, value.value))
            return
        super()._constant(register, value)


class CompiscriptRuntime(BaseRuntime):
    def __init__(self) -> None:
        self._states: dict[MipsEmitter, _ProgramState] = {}

    def _state(self, emitter: MipsEmitter) -> _ProgramState:
        if emitter not in self._states:
            self._states[emitter] = _ProgramState()
        return self._states[emitter]

    # -- data -----------------------------------------------------------------

    def string_literal(self, emitter: MipsEmitter, text: str) -> str:
        """Label of an immutable string object; equal texts share one object."""
        if type(text) is not str:
            raise MipsError('MIPS-TYPE', 'string literal must be text')
        try:
            content = text.encode('utf-8')
        except UnicodeEncodeError as error:
            raise MipsError('MIPS-TYPE', f'string literal is not valid Unicode: {text!r}') from error
        state = self._state(emitter)
        if content not in state.strings:
            label = emitter.label('string')
            emitter.define(label)
            emitter.data.extend(['.align 3', f'{label}: .word {len(content)}, 0'])
            if content:
                emitter.data.append('.byte ' + ', '.join(str(byte) for byte in content))
            state.strings[content] = label
        return state.strings[content]

    def _globals(self, emitter: MipsEmitter) -> _ProgramState:
        """Handler-chain head and error payload: global words, never a hidden ``$s``."""
        state = self._state(emitter)
        if state.head is None:
            state.head, state.payload = emitter.label('handler_head'), emitter.label('error_payload')
            for label in (state.head, state.payload):
                emitter.define(label)
                emitter.data.extend(['.align 3', f'{label}: .word 0, 0'])
        return state

    def handler_head(self, emitter: MipsEmitter) -> str:
        label = self._globals(emitter).head
        emitter.references.add(label)
        return label

    def error_payload(self, emitter: MipsEmitter) -> str:
        label = self._globals(emitter).payload
        emitter.references.add(label)
        return label

    def _helper(self, emitter: MipsEmitter, name: str) -> str:
        state = self._state(emitter)
        if state.emitted:
            raise MipsError('MIPS-INTERNAL', f'helper {name} requested after the runtime was emitted')
        if name not in state.helpers:
            state.helpers[name] = emitter.label(f'rt_{name}')
        state.used.add(name)
        emitter.references.add(state.helpers[name])
        return state.helpers[name]

    # -- errors -----------------------------------------------------------------

    def error(self, context: EmissionContext, code: str) -> None:
        """Non-returning: payload in ``$a0``, then the shared ``raise`` routine.

        Uses only reserved registers and never touches the allocator, exactly
        as block 1's contract demands.
        """
        if code not in ERROR_CODES:
            raise MipsError('MIPS-INTERNAL', f'unknown runtime error code {code}')
        out = context.emitter
        out.emit('la', '$a0', self.string_literal(out, code))
        self._jump(out, self._helper(out, 'raise'))

    @staticmethod
    def _jump(out: MipsEmitter, label: str) -> None:
        out.references.add(label)
        out.emit('j', label)
        out.emit('nop')

    # -- print ------------------------------------------------------------------

    def print_value(self, context: EmissionContext, value: Operand) -> None:
        marker = next((text for kind, text in MARKERS if isinstance(value.type, kind)), None)
        if value.type != STRING and marker is None:
            if value.type == UNKNOWN or value.type is None:
                raise MipsError('MIPS-UNRESOLVED-TYPE', 'print needs a value of known type')
            super().print_value(context, value)
            return
        registers, out = context.registers, context.emitter
        registers.flush()
        register = registers.getReg(value)
        null, end = out.label('print_null'), out.label('printed')
        out.branch('beqz', null, register)
        if marker is None:
            out.emit('lw', '$a2', f'0({register})')
            out.emit('addiu', '$a1', register, str(STRING_HEADER))
            out.emit('li', '$a0', '1')
            out.emit('li', '$v0', '15')
        else:
            out.emit('la', '$a0', out.ascii(marker))
            out.emit('li', '$v0', '4')
        out.emit('syscall')
        out.branch('b', end)
        out.mark(null)
        out.emit('la', '$a0', out.ascii('null'))
        out.emit('li', '$v0', '4')
        out.emit('syscall')
        out.mark(end)
        out.emit('li', '$a0', '10')
        out.emit('li', '$v0', '11')
        out.emit('syscall')
        registers.invalidate()

    # -- strings ----------------------------------------------------------------

    def emit_string(self, instruction: Instruction, context: EmissionContext) -> bool:
        """Every scalar opcode touching a string (called after a register barrier)."""
        op, a, b, result = instruction.quadruple
        registers, out = context.registers, context.emitter
        if result is None or a is None:
            raise MipsError('MIPS-INVALID-IR', f'{op.value} needs operands and a destination')
        if op is OpCode.COPY:
            if a.type not in (STRING, NULL) or result.type != STRING:
                raise MipsError('MIPS-TYPE', 'string copy needs string operands')
            source = registers.getReg(a, pinned=True)
            out.emit('move', '$t8', source)
            registers.unpin(a)
            registers.write(result, '$t8')
            return True
        if b is None or a.type != STRING or b.type != STRING:
            raise MipsError('MIPS-TYPE', f'{op.value} needs two string operands')
        if op is OpCode.ADD:
            if result.type != STRING:
                raise MipsError('MIPS-TYPE', 'concatenation produces a string')
            left, right = self._operands(context, a, b, null_checked=True)
            self._call(context, 'concat', (left, right), (a, b))
            registers.write(result, '$v0')
            return True
        if op in (OpCode.EQ, OpCode.NE) or op in ORDERED:
            if result.type != BOOLEAN:
                raise MipsError('MIPS-TYPE', 'string comparison produces a boolean')
            if op in (OpCode.EQ, OpCode.NE):
                left, right = self._operands(context, a, b, null_checked=False)
                self._call(context, 'equals', (left, right), (a, b))
                out.emit('xori' if op is OpCode.NE else 'move', '$t8', '$v0',
                         *(('1',) if op is OpCode.NE else ()))
            else:
                left, right = self._operands(context, a, b, null_checked=True)
                self._call(context, 'compare', (left, right), (a, b))
                out.emit(ORDERED[op], '$t8', '$v0', '$zero')
            registers.write(result, '$t8')
            return True
        raise MipsError('MIPS-TYPE', f'{op.value} is not defined for strings')

    @staticmethod
    def _operands(context: EmissionContext, a: Operand, b: Operand,
                  null_checked: bool) -> tuple[str, str]:
        registers = context.registers
        left = registers.getReg(a, pinned=True)
        right = registers.getReg(b, pinned=True)
        if null_checked:
            guard(context, 'bnez', (left,), 'NULL_ACCESS')
            guard(context, 'bnez', (right,), 'NULL_ACCESS')
        return left, right

    def _call(self, context: EmissionContext, name: str, arguments: tuple[str, ...],
              pinned: tuple[Operand, ...]) -> None:
        """ABI call of a leaf helper; arguments are copied before the barrier."""
        out, registers = context.emitter, context.registers
        label = self._helper(out, name)
        out.emit('addiu', '$sp', '$sp', str(-8 * len(arguments)))
        for index, register in enumerate(arguments):
            out.emit('sw', register, f'{8 * index}($sp)')
        for operand in pinned:
            registers.unpin(operand)
        registers.flush()
        registers.invalidate()
        out.branch('jal', label)
        out.emit('addiu', '$sp', '$sp', str(8 * len(arguments)))

    # -- helper routines ----------------------------------------------------------

    def emit_helpers(self, emitter: MipsEmitter) -> None:
        """Emit, once and after every unit, the routines the program referenced."""
        state = self._state(emitter)
        if state.emitted:
            raise MipsError('MIPS-INTERNAL', 'runtime helpers emitted twice')
        if 'raise' in state.used:
            self._emit_raise(emitter)
        for name in HELPERS:
            if name in state.used:
                emitter.mark(state.helpers[name])
                getattr(self, f'_emit_{name}')(emitter)
        state.emitted = True

    def _emit_raise(self, out: MipsEmitter) -> None:
        state = self._state(out)
        head, payload = self.handler_head(out), self.error_payload(out)
        out.mark(state.helpers['raise'])
        uncaught = out.label('uncaught')
        out.emit('la', '$t9', payload)
        out.emit('sw', '$a0', '0($t9)')
        out.emit('la', '$t9', head)
        out.emit('lw', '$t8', '0($t9)')
        out.branch('beqz', uncaught, '$t8')
        out.emit('lw', '$v1', '0($t8)')        # the handler is retired before its catch runs
        out.emit('sw', '$v1', '0($t9)')
        for index in range(8):                  # skipped epilogues never restored them
            out.emit('lw', f'$s{index}', f'{SAVED_OFFSET + 4 * index}($t8)')
        out.emit('lw', '$sp', '16($t8)')       # discards abandoned frames and arguments
        out.emit('lw', '$fp', '24($t8)')
        out.emit('lw', '$ra', '32($t8)')
        out.emit('lw', '$v1', '8($t8)')
        out.emit('jr', '$v1')
        out.emit('nop')
        out.mark(uncaught)
        out.emit('la', '$a0', out.ascii('RuntimeError: '))
        out.emit('li', '$v0', '4')
        out.emit('syscall')
        out.emit('la', '$t9', payload)
        out.emit('lw', '$t8', '0($t9)')
        out.emit('lw', '$a2', '0($t8)')
        out.emit('addiu', '$a1', '$t8', str(STRING_HEADER))
        out.emit('li', '$a0', '1')
        out.emit('li', '$v0', '15')
        out.emit('syscall')
        out.emit('li', '$a0', '10')
        out.emit('li', '$v0', '11')
        out.emit('syscall')
        out.emit('li', '$a0', '1')
        out.emit('li', '$v0', '17')
        out.emit('syscall')

    @staticmethod
    def _emit_concat(out: MipsEmitter) -> None:
        """concat(a, b): new object with both contents; operands are non-null."""
        copy_a, copy_b, start_b, done = (out.label(n) for n in ('copy_a', 'copy_b', 'start_b', 'joined'))
        out.emit('lw', '$t8', '0($sp)')
        out.emit('lw', '$t9', '8($sp)')
        out.emit('lw', '$a1', '0($t8)')
        out.emit('lw', '$a2', '0($t9)')
        out.emit('addu', '$a3', '$a1', '$a2')
        out.emit('addiu', '$a0', '$a3', str(STRING_HEADER + 7))
        out.emit('li', '$v0', '9')
        out.emit('syscall')
        out.emit('addiu', '$v0', '$v0', '7')
        out.emit('li', '$v1', '-8')
        out.emit('and', '$v0', '$v0', '$v1')
        out.emit('sw', '$a3', '0($v0)')
        out.emit('sw', '$zero', '4($v0)')
        out.emit('addiu', '$v1', '$v0', str(STRING_HEADER))
        out.emit('addiu', '$a0', '$t8', str(STRING_HEADER))
        for loop, after in ((copy_a, start_b), (copy_b, done)):
            out.mark(loop)
            out.branch('beqz', after, '$a1')
            out.emit('lbu', '$t8', '0($a0)')
            out.emit('sb', '$t8', '0($v1)')
            out.emit('addiu', '$a0', '$a0', '1')
            out.emit('addiu', '$v1', '$v1', '1')
            out.emit('addiu', '$a1', '$a1', '-1')
            out.branch('b', loop)
            out.mark(after)
            if loop is copy_a:
                out.emit('addiu', '$a0', '$t9', str(STRING_HEADER))
                out.emit('move', '$a1', '$a2')
        out.emit('jr', '$ra')
        out.emit('nop')

    @staticmethod
    def _emit_equals(out: MipsEmitter) -> None:
        """equals(a, b) -> 1/0 by content; ``null == null`` and identity are equal."""
        loop, same, done = out.label('equals_loop'), out.label('equals_same'), out.label('equals_done')
        out.emit('lw', '$t8', '0($sp)')
        out.emit('lw', '$t9', '8($sp)')
        out.emit('li', '$v0', '1')
        out.branch('beq', done, '$t8', '$t9')
        out.emit('li', '$v0', '0')
        out.branch('beqz', done, '$t8')
        out.branch('beqz', done, '$t9')
        out.emit('lw', '$a1', '0($t8)')
        out.emit('lw', '$a2', '0($t9)')
        out.branch('bne', done, '$a1', '$a2')
        out.emit('addiu', '$a0', '$t8', str(STRING_HEADER))
        out.emit('addiu', '$a3', '$t9', str(STRING_HEADER))
        out.mark(loop)
        out.branch('beqz', same, '$a1')
        out.emit('lbu', '$t8', '0($a0)')
        out.emit('lbu', '$t9', '0($a3)')
        out.branch('bne', done, '$t8', '$t9')
        out.emit('addiu', '$a0', '$a0', '1')
        out.emit('addiu', '$a3', '$a3', '1')
        out.emit('addiu', '$a1', '$a1', '-1')
        out.branch('b', loop)
        out.mark(same)
        out.emit('li', '$v0', '1')
        out.mark(done)
        out.emit('jr', '$ra')
        out.emit('nop')

    @staticmethod
    def _emit_compare(out: MipsEmitter) -> None:
        """compare(a, b) -> -1/0/1 by unsigned UTF-8 bytes; operands are non-null."""
        loop, differ, a_end, less, greater, equal = (
            out.label(n) for n in ('compare_loop', 'differ', 'a_end', 'less', 'greater', 'equal'))
        out.emit('lw', '$t8', '0($sp)')
        out.emit('lw', '$t9', '8($sp)')
        out.emit('lw', '$a1', '0($t8)')
        out.emit('lw', '$a2', '0($t9)')
        out.emit('addiu', '$a0', '$t8', str(STRING_HEADER))
        out.emit('addiu', '$a3', '$t9', str(STRING_HEADER))
        out.mark(loop)
        out.branch('beqz', a_end, '$a1')
        out.branch('beqz', greater, '$a2')
        out.emit('lbu', '$t8', '0($a0)')
        out.emit('lbu', '$t9', '0($a3)')
        out.branch('bne', differ, '$t8', '$t9')
        out.emit('addiu', '$a0', '$a0', '1')
        out.emit('addiu', '$a3', '$a3', '1')
        out.emit('addiu', '$a1', '$a1', '-1')
        out.emit('addiu', '$a2', '$a2', '-1')
        out.branch('b', loop)
        out.mark(differ)
        out.emit('sltu', '$v0', '$t8', '$t9')
        out.branch('bnez', less, '$v0')
        out.branch('b', greater)
        out.mark(a_end)
        out.branch('beqz', equal, '$a2')
        out.mark(less)
        out.emit('li', '$v0', '-1')
        out.emit('jr', '$ra')
        out.emit('nop')
        out.mark(greater)
        out.emit('li', '$v0', '1')
        out.emit('jr', '$ra')
        out.emit('nop')
        out.mark(equal)
        out.emit('li', '$v0', '0')
        out.emit('jr', '$ra')
        out.emit('nop')

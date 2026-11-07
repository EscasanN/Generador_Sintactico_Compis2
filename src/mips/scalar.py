"""TAC scalar handler; extensions compose without importing future backends."""
from src.codegen.ir import IRProgram, Instruction, OpCode as O
from src.codegen.verifier import IRVerifier
from src.mips.diagnostics import MipsError
from src.mips.models import EmissionContext
from src.semantic.types import (
    BOOLEAN, FLOAT, INTEGER, NULL, STRING, ArrayType, ClassType, FunctionType, is_assignable,
)


ARITHMETIC = {O.ADD, O.SUB, O.MUL, O.DIV, O.MOD}
COMPARE = {O.EQ, O.NE, O.LT, O.LE, O.GT, O.GE}
SCALAR_OPCODES = frozenset({O.COPY, *ARITHMETIC, *COMPARE, O.NEG, O.NOT, O.CAST,
                          O.LABEL, O.GOTO, O.IF_TRUE, O.IF_FALSE, O.RELEASE})


class ScalarLowerer:
    def __init__(self) -> None:
        self._labels: dict[tuple, str] = {}

    def supports(self, opcode: O) -> bool:
        return opcode in SCALAR_OPCODES

    def lower(self, instructions: tuple[Instruction, ...] | list[Instruction],
              context: EmissionContext) -> None:
        """Checked standalone global IR entry. Full pipeline validates whole IR in block 3."""
        if context.procedure != 'global':
            raise MipsError('MIPS-INVALID-IR', 'lower validates global IR; use emit for procedures')
        errors = IRVerifier().verify(IRProgram(tuple(instructions)))
        if errors:
            raise MipsError('MIPS-INVALID-IR', errors[0].message, errors[0].location)
        for instruction in instructions:
            self.emit(instruction, context)

    def _label(self, name: str, context: EmissionContext) -> str:
        key = context.emitter, context.procedure, name
        if key not in self._labels:
            self._labels[key] = context.emitter.label(name)
        return self._labels[key]

    def emit(self, instruction: Instruction, context: EmissionContext) -> None:
        op, a, b, result = instruction.quadruple
        out, regs = context.emitter, context.registers
        if not self.supports(op):
            raise MipsError('MIPS-UNSUPPORTED-OPCODE', op.value, instruction.source_location)
        if instruction.source_location is not None:
            out.source_map[len(out.text)] = instruction.source_location
        try:
            if op is O.RELEASE:
                regs.release(a)
                return
            if op in (O.LABEL, O.GOTO, O.IF_TRUE, O.IF_FALSE):
                regs.flush()
                regs.invalidate()
                label = self._label(str(result.value), context)
                if op is O.LABEL:
                    # Text order stops being execution order here; IRVerifier checks each path.
                    regs.released.clear()
                    out.mark(label)
                elif op is O.GOTO:
                    out.branch('b', label)
                else:
                    if a.type != BOOLEAN:
                        raise MipsError('MIPS-TYPE', 'branch condition must be boolean')
                    register = regs.getReg(a)
                    out.branch('bnez' if op is O.IF_TRUE else 'beqz', label, register)
                    regs.invalidate()
                return
            if any(value is not None and value.type == STRING for value in (a, b, result)):
                regs.flush()
                regs.invalidate()
                if not context.runtime.emit_string(instruction, context):
                    raise MipsError('MIPS-UNSUPPORTED-TYPE', 'string runtime provider required')
                return
            self._validate(instruction)
            x = regs.getReg(a, pinned=True)
            y = regs.getReg(b, pinned=True) if b is not None and op is not O.CAST else None
            scratch = '$f14' if result.type == FLOAT else '$t8'
            if op is O.COPY:
                out.emit('mov.d' if result.type == FLOAT else 'move', scratch, x)
            elif op is O.CAST:
                if a.type == result.type:
                    out.emit('mov.d' if result.type == FLOAT else 'move', scratch, x)
                elif a.type == INTEGER and result.type == FLOAT:
                    out.emit('mtc1', x, '$f14')
                    out.emit('cvt.d.w', '$f14', '$f14')
                else:
                    raise MipsError('MIPS-TYPE', 'unsupported CAST')
            elif op is O.NEG:
                out.emit('neg.d', scratch, x) if result.type == FLOAT else out.emit('subu', scratch, '$zero', x)
            elif op is O.NOT:
                out.emit('sltiu', scratch, x, '1')
            elif a.type == FLOAT:
                self._floating(op, x, y, context)
            else:
                self._integer(op, x, y, context)
            regs.unpin(a)
            if b is not None and op is not O.CAST:
                regs.unpin(b)
            regs.write(result, scratch)
        except MipsError as error:
            if error.diagnostic.location is None:
                raise MipsError(error.diagnostic.code, error.diagnostic.message,
                                instruction.source_location) from error
            raise

    @staticmethod
    def _validate(item: Instruction) -> None:
        op, a, b, result = item.quadruple
        if a is None or result is None:
            raise MipsError('MIPS-INVALID-IR', 'missing scalar operands')
        if op is O.COPY:
            reference_copy = (isinstance(result.type, (ArrayType, ClassType, FunctionType))
                              and is_assignable(a.type, result.type))
            if a.type != result.type and not reference_copy:
                raise MipsError('MIPS-TYPE', 'copy needs compatible representation')
        elif op is O.CAST:
            if b is None or str(b.value) != str(result.type):
                raise MipsError('MIPS-TYPE', 'CAST target mismatch')
        elif op is O.NOT:
            if a.type != BOOLEAN or result.type != BOOLEAN:
                raise MipsError('MIPS-TYPE', 'NOT requires boolean')
        elif op is O.NEG:
            if a.type not in (INTEGER, FLOAT) or a.type != result.type:
                raise MipsError('MIPS-TYPE', 'NEG requires same numeric type')
        else:
            reference_comparison = (b is not None and op in (O.EQ, O.NE)
                                    and (is_assignable(a.type, b.type) or is_assignable(b.type, a.type))
                                    and (a.type == NULL or isinstance(a.type, (ArrayType, ClassType, FunctionType)))
                                    and (b.type == NULL or isinstance(b.type, (ArrayType, ClassType, FunctionType))))
            if b is None or a.type != b.type and not reference_comparison:
                raise MipsError('MIPS-TYPE', 'binary operands require matching types')
            if op in ARITHMETIC and (a.type not in (INTEGER, FLOAT) or result.type != a.type):
                raise MipsError('MIPS-TYPE', 'arithmetic requires matching numeric types')
            if op in COMPARE and (result.type != BOOLEAN or a.type not in (INTEGER, FLOAT, BOOLEAN, NULL)
                                 and not isinstance(a.type, (ArrayType, ClassType, FunctionType))):
                raise MipsError('MIPS-TYPE', 'comparison requires a scalar/runtime provider')
            if op in (O.LT, O.LE, O.GT, O.GE) and a.type not in (INTEGER, FLOAT):
                raise MipsError('MIPS-TYPE', 'ordered comparison requires numeric values')

    def _zero_check(self, register: str, floating: bool, context: EmissionContext) -> None:
        out = context.emitter
        ok = out.label('nonzero')
        # The descriptors are shared by both outgoing paths: materialize on
        # both, not only on the exceptional branch (which would lose values
        # later evicted on the successful path).
        context.registers.flush()
        if floating:
            out.emit('l.d', '$f16', out.double(0.0))
            out.emit('c.eq.d', register, '$f16')
            out.branch('bc1f', ok)
        else:
            out.branch('bnez', ok, register)
        context.runtime.error(context, 'DIV_ZERO')
        out.mark(ok)

    def _integer(self, op: O, x: str, y: str, context: EmissionContext) -> None:
        out = context.emitter
        simple = {O.ADD: 'addu', O.SUB: 'subu', O.MUL: 'mul', O.EQ: 'seq', O.NE: 'sne',
                  O.LT: 'slt', O.LE: 'sle', O.GT: 'sgt', O.GE: 'sge'}
        if op in simple:
            out.emit(simple[op], '$t8', x, y)
            return
        self._zero_check(y, False, context)
        normal, done = out.label('divide'), out.label('division_done')
        out.emit('li', '$t9', '-2147483648')
        out.branch('bne', normal, x, '$t9')
        out.emit('li', '$t9', '-1')
        out.branch('bne', normal, y, '$t9')
        out.emit('li', '$t8', '-2147483648' if op is O.DIV else '0')
        out.branch('b', done)
        out.mark(normal)
        out.emit('div', '$zero', x, y)
        out.emit('mflo' if op is O.DIV else 'mfhi', '$t8')
        out.mark(done)

    def _floating(self, op: O, x: str, y: str, context: EmissionContext) -> None:
        out = context.emitter
        if op in COMPARE:
            out.emit('li', '$t8', '1' if op is O.NE else '0')
            if op in (O.EQ, O.NE):
                comparison, left, right = 'c.eq.d', x, y
            elif op in (O.GT, O.GE):
                comparison, left, right = ('c.lt.d' if op is O.GT else 'c.le.d'), y, x
            else:
                comparison, left, right = ('c.lt.d' if op is O.LT else 'c.le.d'), x, y
            out.emit(comparison, left, right)
            done = out.label('compare_done')
            out.branch('bc1f', done)
            out.emit('li', '$t8', '0' if op is O.NE else '1')
            out.mark(done)
        elif op is O.MOD:
            self._zero_check(y, True, context)
            self._remainder(x, y, context)
        else:
            if op is O.DIV:
                self._zero_check(y, True, context)
            out.emit({O.ADD: 'add.d', O.SUB: 'sub.d', O.MUL: 'mul.d', O.DIV: 'div.d'}[op], '$f14', x, y)

    @staticmethod
    def _remainder(x: str, y: str, context: EmissionContext) -> None:
        """Binary magnitude reduction; never converts a huge quotient to int32.

        Subtractions occur only between comparable magnitudes (Sterbenz), so
        the algorithm also handles subnormal divisors and signed zero.
        Uses reserved helper scratch f14..f24, never allocator-owned registers.
        """
        out = context.emitter
        nan, sign, end = out.label('remainder_nan'), out.label('remainder_sign'), out.label('remainder_end')
        scale, scaled, reduce, half = (out.label(n) for n in ('scale', 'scaled', 'reduce', 'half'))
        out.emit('abs.d', '$f14', x)
        out.emit('abs.d', '$f16', y)
        out.emit('l.d', '$f22', out.double(2.0))
        out.emit('l.d', '$f24', out.double(float('inf')))
        out.emit('c.eq.d', '$f14', '$f14')
        out.branch('bc1f', nan)
        out.emit('c.eq.d', '$f16', '$f16')
        out.branch('bc1f', nan)
        out.emit('c.eq.d', '$f14', '$f24')
        out.branch('bc1t', nan)
        out.emit('c.lt.d', '$f14', '$f16')
        out.branch('bc1t', sign)
        out.emit('mov.d', '$f18', '$f16')
        out.mark(scale)
        out.emit('sub.d', '$f20', '$f14', '$f18')
        out.emit('c.le.d', '$f18', '$f20')
        out.branch('bc1f', scaled)
        out.emit('add.d', '$f18', '$f18', '$f18')
        out.branch('b', scale)
        out.mark(scaled)
        out.mark(reduce)
        out.emit('c.le.d', '$f18', '$f14')
        out.branch('bc1f', half)
        out.emit('sub.d', '$f14', '$f14', '$f18')
        out.mark(half)
        out.emit('c.eq.d', '$f18', '$f16')
        out.branch('bc1t', sign)
        out.emit('div.d', '$f18', '$f18', '$f22')
        out.branch('b', reduce)
        out.mark(sign)
        out.emit('mfc1', '$t9', f'$f{int(x[2:]) + 1}')
        out.branch('bgez', end, '$t9')
        out.emit('neg.d', '$f14', '$f14')
        out.branch('b', end)
        out.mark(nan)
        out.emit('l.d', '$f14', out.double(float('nan')))
        out.mark(end)

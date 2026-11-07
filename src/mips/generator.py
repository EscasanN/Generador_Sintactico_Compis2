"""Complete MIPS generation from a verified TAC result (block 3).

``generate_mips`` composes the handlers of the three backend blocks into one
registry where every ``OpCode`` has exactly one owner:

======================  =======================================  =======
opcodes                 handler                                  block
======================  =======================================  =======
scalars, flow, RELEASE  ``ScalarLowerer``                        1
PARAM, CALL, ...        ``CallingConvention``                    2
ENV_*, CLOSURE, ...     ``EnvironmentHandler``                   2
LIST_*                  ``ListHandler``                          3
OBJECT_NEW, FIELD_*     ``ObjectHandler``                        3
TRY_*, CATCH            ``ExceptionHandler``                     3
======================  =======================================  =======

Strings reach ``CompiscriptRuntime.emit_string`` through the scalar handler and
``print`` reaches ``CompiscriptRuntime.print_value`` through the calls handler.

The generator validates its input, plans every frame, checks that each opcode
in the program has a handler, emits the program and publishes the assembly
only when everything succeeded: a rejection carries located diagnostics and no
assembly.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence

from src.codegen.ir import IRProgram, Instruction, OpCode
from src.codegen.results import IntermediateCodeResult
from src.codegen.verifier import IRVerifier
from src.mips.calls import ProgramEmitter
from src.mips.diagnostics import MipsDiagnostic, MipsError
from src.mips.emitter import MipsEmitter
from src.mips.exceptions import ExceptionHandler
from src.mips.layout import GLOBAL_UNIT, PhysicalLayoutPlan
from src.mips.lists import ListHandler
from src.mips.models import EmissionContext, MipsGenerationResult
from src.mips.objects import ObjectHandler
from src.mips.runtime import CompiscriptRuntime, RuntimeRegisterAllocator
from src.mips.scalar import ScalarLowerer


class MipsProgramEmitter(ProgramEmitter):
    """Block 2's reference composition plus the block 3 handlers and runtime.

    Each unit gets a ``RuntimeRegisterAllocator`` (string literals become
    addresses) and the runtime's helper routines are emitted once, after the
    last unit, so they are never reached by falling through.
    """

    def __init__(self, plan: PhysicalLayoutPlan, runtime: CompiscriptRuntime | None = None, *,
                 gpr_count: int = 8, fpr_count: int = 5) -> None:
        runtime = runtime or CompiscriptRuntime()
        super().__init__(plan, runtime, gpr_count=gpr_count, fpr_count=fpr_count)
        self.scalar = next(h for h in self.handlers if isinstance(h, ScalarLowerer))
        self.handlers.extend([ListHandler(), ObjectHandler(plan),
                              ExceptionHandler(self.scalar._label)])
        self._final_unit = GLOBAL_UNIT

    def handler_for(self, opcode: OpCode) -> list[object]:
        return [handler for handler in self.handlers if handler.supports(opcode)]

    def check_coverage(self, program: IRProgram) -> None:
        """Every opcode used has exactly one handler: nothing becomes a silent ``nop``."""
        for item in (*program.global_code, *(i for p in program.procedures for i in p.instructions)):
            owners = self.handler_for(item.opcode)
            if not owners:
                raise MipsError('MIPS-UNSUPPORTED-OPCODE', item.opcode.value, item.source_location)
            if len(owners) > 1:
                raise MipsError('MIPS-INTERNAL', f'{item.opcode.value} has several handlers',
                                item.source_location)

    def assemble(self, program: IRProgram, **hooks) -> str:
        self.check_coverage(program)
        self._final_unit = str(program.procedures[-1].label.value) if program.procedures else GLOBAL_UNIT
        return super().assemble(program, **hooks)

    def _unit(self, emitter: MipsEmitter, name: str, instructions: Sequence[Instruction],
              begin: Callable, end: Callable) -> None:
        registers = RuntimeRegisterAllocator(emitter, self.plan, name, runtime=self.runtime,
                                             gpr_count=self.counts[0], fpr_count=self.counts[1])
        context = EmissionContext(emitter, registers, self.plan, self.runtime, name)
        begin(context)
        for item in instructions:
            self._dispatch(item, context)
        end(context)
        self.per_procedure[name] = {
            'stack_bytes': self.plan.frame(name).size, 'spills': registers.spills,
            'reloads': registers.reloads,
        }
        if name == self._final_unit:
            self.runtime.emit_helpers(emitter)


def _diagnostic(error: MipsError) -> MipsDiagnostic:
    return error.diagnostic


def generate_mips(intermediate_result: IntermediateCodeResult, *, gpr_count: int = 8,
                  fpr_count: int = 5) -> MipsGenerationResult:
    """Translate an accepted TAC result to MIPS32 for MARS; never partial assembly.

    The register bank sizes may be reduced (as in block 1's tests) to exercise
    spills; the defaults use the whole allocatable bank.
    """
    if not isinstance(intermediate_result, IntermediateCodeResult):
        return MipsGenerationResult(diagnostics=(MipsDiagnostic(
            'MIPS-INVALID-IR', 'generate_mips needs an IntermediateCodeResult'),))
    if not intermediate_result.accepted or intermediate_result.program is None:
        return MipsGenerationResult(diagnostics=(MipsDiagnostic(
            'MIPS-INVALID-IR', 'MIPS is generated only from an accepted TAC result'),))
    if intermediate_result.layouts is None:
        return MipsGenerationResult(diagnostics=(MipsDiagnostic(
            'MIPS-MISSING-LAYOUT', 'the TAC result has no runtime layouts'),))
    program = intermediate_result.program
    errors = IRVerifier().verify(program)
    if errors:
        return MipsGenerationResult(diagnostics=(MipsDiagnostic(
            'MIPS-INVALID-IR', errors[0].message, errors[0].location),))
    try:
        plan = PhysicalLayoutPlan.build(program, intermediate_result.layouts)
        emitter = MipsProgramEmitter(plan, gpr_count=gpr_count, fpr_count=fpr_count)
        assembly = emitter.assemble(program)
    except MipsError as error:
        return MipsGenerationResult(diagnostics=(_diagnostic(error),))
    except LookupError as error:
        return MipsGenerationResult(diagnostics=(MipsDiagnostic('MIPS-MISSING-LAYOUT', str(error)),))
    return MipsGenerationResult(assembly, (), plan, emitter.statistics)

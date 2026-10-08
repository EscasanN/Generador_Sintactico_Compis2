"""Structural and control-flow checks for intermediate programs."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from src.codegen.ir import IRProgram, Instruction, OpCode, Operand, OperandKind
from src.semantic.diagnostics import SourceLocation


@dataclass(frozen=True, slots=True)
class IRDiagnostic:
    code: str
    message: str
    location: SourceLocation | None = None


_BINARY = {
    OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, OpCode.MOD,
    OpCode.EQ, OpCode.NE, OpCode.LT, OpCode.LE, OpCode.GT, OpCode.GE,
}
_UNARY = {OpCode.NEG, OpCode.NOT, OpCode.LIST_NEW, OpCode.LIST_LEN, OpCode.ENV_NEW}
_STORES = {OpCode.LIST_SET, OpCode.FIELD_SET, OpCode.ENV_SET}
_TWO_INPUT = {
    OpCode.LIST_GET, OpCode.FIELD_GET, OpCode.METHOD_REF, OpCode.ENV_GET,
    OpCode.CLOSURE, OpCode.OBJECT_NEW, OpCode.CAST, OpCode.CALL,
    OpCode.CLOSURE_CALL,
}
_DEFINES = {OpCode.COPY, *_BINARY, *_UNARY, *_TWO_INPUT, OpCode.CATCH}
_SHAPES: dict[OpCode, tuple[bool, bool, bool]] = {
    **{opcode: (True, True, True) for opcode in _BINARY | _TWO_INPUT},
    **{opcode: (True, False, True) for opcode in _UNARY | {OpCode.COPY}},
    **{opcode: (True, True, True) for opcode in _STORES},
    OpCode.LABEL: (False, False, True),
    OpCode.GOTO: (False, False, True),
    OpCode.IF_TRUE: (True, False, True),
    OpCode.IF_FALSE: (True, False, True),
    OpCode.PARAM: (True, False, False),
    OpCode.RETURN: (False, False, False),
    OpCode.RELEASE: (True, False, False),
    OpCode.TRY_BEGIN: (False, False, True),
    OpCode.TRY_END: (False, False, False),
    OpCode.CATCH: (False, False, True),
}
_VALUE = frozenset({OperandKind.CONSTANT, OperandKind.SYMBOL, OperandKind.TEMPORARY})
_DESTINATION = frozenset({OperandKind.SYMBOL, OperandKind.TEMPORARY})
_LABEL = frozenset({OperandKind.LABEL})
_OFFSET = frozenset({OperandKind.OFFSET})
_CONSTANT = frozenset({OperandKind.CONSTANT})
_TEMPORARY = frozenset({OperandKind.TEMPORARY})
_CALL_TARGET = frozenset({OperandKind.SYMBOL, OperandKind.TEMPORARY})
_KIND_RULES: dict[
    OpCode,
    tuple[frozenset[OperandKind] | None, frozenset[OperandKind] | None,
          frozenset[OperandKind] | None],
] = {
    **{opcode: (_VALUE, _VALUE, _DESTINATION) for opcode in _BINARY},
    OpCode.COPY: (_VALUE, None, _DESTINATION),
    OpCode.NEG: (_VALUE, None, _DESTINATION),
    OpCode.NOT: (_VALUE, None, _DESTINATION),
    OpCode.CAST: (_VALUE, _LABEL, _DESTINATION),
    OpCode.LABEL: (None, None, _LABEL),
    OpCode.GOTO: (None, None, _LABEL),
    OpCode.IF_TRUE: (_VALUE, None, _LABEL),
    OpCode.IF_FALSE: (_VALUE, None, _LABEL),
    OpCode.PARAM: (_VALUE, None, None),
    OpCode.CALL: (_LABEL, _CONSTANT, _DESTINATION),
    OpCode.CLOSURE_CALL: (_CALL_TARGET, _CONSTANT, _DESTINATION),
    OpCode.RETURN: (_VALUE, None, None),
    OpCode.LIST_NEW: (_CONSTANT, None, _DESTINATION),
    OpCode.LIST_SET: (_VALUE, _VALUE, _VALUE),
    OpCode.LIST_GET: (_VALUE, _VALUE, _DESTINATION),
    OpCode.LIST_LEN: (_VALUE, None, _DESTINATION),
    OpCode.OBJECT_NEW: (_LABEL, _CONSTANT, _DESTINATION),
    OpCode.FIELD_SET: (_VALUE, _OFFSET, _VALUE),
    OpCode.FIELD_GET: (_VALUE, _OFFSET, _DESTINATION),
    OpCode.METHOD_REF: (_VALUE, _LABEL, _DESTINATION),
    OpCode.ENV_NEW: (_CONSTANT, None, _DESTINATION),
    OpCode.ENV_SET: (_VALUE, _OFFSET, _VALUE),
    OpCode.ENV_GET: (_VALUE, _OFFSET, _DESTINATION),
    OpCode.CLOSURE: (_LABEL, _VALUE, _DESTINATION),
    OpCode.TRY_BEGIN: (None, None, _LABEL),
    OpCode.TRY_END: (None, None, None),
    OpCode.CATCH: (None, None, _DESTINATION),
    OpCode.RELEASE: (_TEMPORARY, None, None),
}


def _key(operand: Operand) -> tuple[str, tuple[int, int] | None]:
    return str(operand.value), operand.lease


class IRVerifier:
    """Return IR diagnostics without mutating or formatting the program."""

    def verify(self, program: IRProgram) -> tuple[IRDiagnostic, ...]:
        diagnostics: list[IRDiagnostic] = []
        procedure_labels: set[str] = set()
        for procedure in program.procedures:
            label = str(procedure.label.value)
            if label in procedure_labels:
                diagnostics.append(IRDiagnostic(
                    "IR-PROCEDURE-DUPLICATE", f"duplicate procedure {label}"
                ))
            procedure_labels.add(label)
        self._verify_unit(program.global_code, diagnostics, "global")
        for procedure in program.procedures:
            self._verify_unit(procedure.instructions, diagnostics, str(procedure.label.value))
            if not procedure.instructions or procedure.instructions[-1].opcode not in (
                OpCode.RETURN, OpCode.GOTO
            ):
                diagnostics.append(IRDiagnostic(
                    "IR-PROCEDURE-OPEN",
                    f"procedure {procedure.label.value} has no terminal transfer",
                ))
        return tuple(diagnostics)

    def _verify_unit(
        self,
        instructions: tuple[Instruction, ...],
        diagnostics: list[IRDiagnostic],
        unit: str,
    ) -> None:
        labels: dict[str, int] = {}
        for index, item in enumerate(instructions):
            if item.source_location is None:
                diagnostics.append(IRDiagnostic(
                    "IR-LOCATION", f"missing location in {unit} at {index}"
                ))
            self._check_shape(item, diagnostics)
            if item.opcode is OpCode.LABEL and item.result is not None:
                name = str(item.result.value)
                if name in labels:
                    diagnostics.append(IRDiagnostic(
                        "IR-LABEL-DUPLICATE", f"duplicate label {name}", item.source_location
                    ))
                labels[name] = index

        for item in instructions:
            if item.opcode in (OpCode.GOTO, OpCode.IF_TRUE, OpCode.IF_FALSE, OpCode.TRY_BEGIN):
                if item.result is not None and str(item.result.value) not in labels:
                    diagnostics.append(IRDiagnostic(
                        "IR-LABEL-MISSING",
                        f"undefined label {item.result.value}",
                        item.source_location,
                    ))

        pending = 0
        for item in instructions:
            if item.opcode is OpCode.PARAM:
                pending += 1
            elif item.opcode in (OpCode.CALL, OpCode.CLOSURE_CALL):
                count = item.arg2.value if item.arg2 is not None else None
                if (
                    not isinstance(count, int)
                    or isinstance(count, bool)
                    or count < 0
                    or count != pending
                ):
                    diagnostics.append(IRDiagnostic(
                        "IR-CALL-ARITY",
                        f"call expects {count} arguments; found {pending}",
                        item.source_location,
                    ))
                pending = 0
            elif pending and item.opcode not in (OpCode.RELEASE,):
                diagnostics.append(IRDiagnostic(
                    "IR-CALL-ARITY", "PARAM sequence interrupted", item.source_location
                ))
                pending = 0
        if pending:
            diagnostics.append(IRDiagnostic("IR-CALL-ARITY", "unconsumed PARAM sequence"))

        self._check_temporaries(instructions, labels, diagnostics)

    def _check_shape(self, item: Instruction, diagnostics: list[IRDiagnostic]) -> None:
        expected = _SHAPES.get(item.opcode)
        if expected is None:
            diagnostics.append(IRDiagnostic("IR-OPCODE", "unknown opcode", item.source_location))
            return
        actual = (item.arg1 is not None, item.arg2 is not None, item.result is not None)
        valid = actual == expected
        if item.opcode is OpCode.RETURN:
            valid = item.arg2 is None and item.result is None
        elif item.opcode in (OpCode.CALL, OpCode.CLOSURE_CALL):
            valid = item.arg1 is not None and item.arg2 is not None
        if not valid:
            diagnostics.append(IRDiagnostic(
                "IR-ARITY", f"invalid operands for {item.opcode.value}", item.source_location
            ))
        kind_rules = _KIND_RULES[item.opcode]
        for operand, allowed in zip(
            (item.arg1, item.arg2, item.result), kind_rules
        ):
            if allowed is not None:
                self._require_kind(operand, allowed, item, diagnostics)

    @staticmethod
    def _require_kind(
        operand: Operand | None,
        allowed: frozenset[OperandKind],
        item: Instruction,
        diagnostics: list[IRDiagnostic],
    ) -> None:
        if operand is not None and operand.kind not in allowed:
            diagnostics.append(IRDiagnostic(
                "IR-OPERAND-KIND",
                f"invalid {operand.kind.value} operand for {item.opcode.value}",
                item.source_location,
            ))

    def _check_temporaries(
        self,
        instructions: tuple[Instruction, ...],
        labels: dict[str, int],
        diagnostics: list[IRDiagnostic],
    ) -> None:
        if not instructions:
            return
        released: set[tuple[str, tuple[int, int] | None]] = set()
        for item in instructions:
            if item.opcode in _DEFINES and item.result is not None:
                if item.result.kind is OperandKind.TEMPORARY and _key(item.result) in released:
                    diagnostics.append(IRDiagnostic(
                        "IR-TEMP-STALE",
                        f"released temporary {item.result.value} is redefined",
                        item.source_location,
                    ))
            if item.opcode is OpCode.RELEASE and item.arg1 is not None:
                if item.arg1.kind is OperandKind.TEMPORARY:
                    released.add(_key(item.arg1))
        states: dict[int, set[tuple[str, tuple[int, int] | None]]] = {0: set()}
        queue = deque([0])
        while queue:
            index = queue.popleft()
            item = instructions[index]
            outgoing = self._transfer(item, states[index])
            for successor in self._successors(index, item, len(instructions), labels):
                previous = states.get(successor)
                merged = outgoing.copy() if previous is None else previous & outgoing
                if previous is None or merged != previous:
                    states[successor] = merged
                    queue.append(successor)

        # Validate disconnected dead code as independent regions. Invalid IR
        # must not evade checks merely by sitting behind an unconditional jump.
        remaining = set(range(len(instructions))) - set(states)
        while remaining:
            seed = min(remaining)
            dead_states: dict[int, set[tuple[str, tuple[int, int] | None]]] = {
                seed: set()
            }
            dead_queue = deque([seed])
            while dead_queue:
                index = dead_queue.popleft()
                outgoing = self._transfer(instructions[index], dead_states[index])
                for successor in self._successors(
                    index, instructions[index], len(instructions), labels
                ):
                    if successor not in remaining:
                        continue
                    previous = dead_states.get(successor)
                    merged = outgoing.copy() if previous is None else previous & outgoing
                    if previous is None or merged != previous:
                        dead_states[successor] = merged
                        dead_queue.append(successor)
            states.update(dead_states)
            remaining.difference_update(dead_states)

        seen: set[tuple[int, str]] = set()
        for index, active in states.items():
            item = instructions[index]
            for operand in self._uses(item):
                if operand.kind is OperandKind.TEMPORARY and _key(operand) not in active:
                    marker = (index, "IR-TEMP-UNDEFINED")
                    if marker not in seen:
                        diagnostics.append(IRDiagnostic(
                            "IR-TEMP-UNDEFINED",
                            f"temporary {operand.value} is not live",
                            item.source_location,
                        ))
                        seen.add(marker)
            if (
                item.opcode in _DEFINES
                and item.result is not None
                and item.result.kind is OperandKind.TEMPORARY
            ):
                if any(
                    name == item.result.value and lease != item.result.lease
                    for name, lease in active
                ):
                    diagnostics.append(IRDiagnostic(
                        "IR-TEMP-COLLISION",
                        f"temporary {item.result.value} is still live",
                        item.source_location,
                    ))

    @staticmethod
    def _uses(item: Instruction) -> tuple[Operand, ...]:
        operands = (item.arg1, item.arg2)
        if item.opcode in _STORES:
            operands += (item.result,)
        return tuple(operand for operand in operands if operand is not None)

    @staticmethod
    def _transfer(
        item: Instruction,
        active: set[tuple[str, tuple[int, int] | None]],
    ) -> set[tuple[str, tuple[int, int] | None]]:
        outgoing = active.copy()
        if (
            item.opcode is OpCode.RELEASE
            and item.arg1 is not None
            and item.arg1.kind is OperandKind.TEMPORARY
        ):
            outgoing.discard(_key(item.arg1))
        if (
            item.opcode in _DEFINES
            and item.result is not None
            and item.result.kind is OperandKind.TEMPORARY
        ):
            outgoing.add(_key(item.result))
        return outgoing

    @staticmethod
    def _successors(
        index: int,
        item: Instruction,
        length: int,
        labels: dict[str, int],
    ) -> tuple[int, ...]:
        target = labels.get(str(item.result.value)) if item.result is not None else None
        if item.opcode is OpCode.RETURN:
            return ()
        if item.opcode is OpCode.GOTO:
            return (target,) if target is not None else ()
        following = (index + 1,) if index + 1 < length else ()
        if item.opcode in (OpCode.IF_TRUE, OpCode.IF_FALSE) and target is not None:
            return following + (target,)
        return following

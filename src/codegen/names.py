"""Unique labels and safely recyclable temporary operands."""

from __future__ import annotations

from itertools import count

from src.codegen.ir import Operand, OperandKind
from src.semantic.types import Type


_pool_ids = count()


class LabelFactory:
    """Issue labels unique within one compilation unit."""

    def __init__(self) -> None:
        self._number = 0
        self._used: set[str] = set()

    def next(self, prefix: str = "L") -> Operand:
        if not prefix:
            raise ValueError("label prefix cannot be empty")
        while True:
            name = f"{prefix}{self._number}"
            self._number += 1
            if name not in self._used:
                self._used.add(name)
                return Operand(OperandKind.LABEL, name)


class TemporaryPool:
    """Manage typed temporary leases; a recycled name gets a new lease."""

    def __init__(self) -> None:
        self._pool_id = next(_pool_ids)
        self._next_name = 0
        self._next_lease = 0
        self._active: dict[str, Operand] = {}
        self._free: list[tuple[str, Type]] = []
        self._peak = 0

    def acquire(self, type_: Type) -> Operand:
        for index in range(len(self._free) - 1, -1, -1):
            name, available_type = self._free[index]
            if available_type == type_:
                self._free.pop(index)
                break
        else:
            name = f"t{self._next_name}"
            self._next_name += 1
        temporary = Operand(
            OperandKind.TEMPORARY,
            name,
            type_,
            (self._pool_id, self._next_lease),
        )
        self._next_lease += 1
        if name in self._active:
            raise RuntimeError(f"temporary collision: {name}")
        self._active[name] = temporary
        self._peak = max(self._peak, len(self._active))
        return temporary

    def validate(self, temporary: Operand) -> None:
        """Reject a foreign, released, or superseded lease."""
        if temporary.kind is not OperandKind.TEMPORARY:
            raise TypeError("expected a temporary operand")
        if self._active.get(str(temporary.value)) != temporary:
            raise ValueError(f"temporary is not active: {temporary.value}")

    def release(self, temporary: Operand) -> None:
        self.validate(temporary)
        del self._active[str(temporary.value)]
        assert temporary.type is not None
        self._free.append((str(temporary.value), temporary.type))

    def is_active(self, temporary: Operand) -> bool:
        return self._active.get(str(temporary.value)) == temporary

    @property
    def active_count(self) -> int:
        return len(self._active)

    @property
    def active_operands(self) -> tuple[Operand, ...]:
        """Snapshot of active leases, used when closing a procedure."""
        return tuple(self._active.values())

    @property
    def peak_active(self) -> int:
        return self._peak

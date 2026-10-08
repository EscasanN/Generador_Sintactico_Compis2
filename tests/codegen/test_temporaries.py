import pytest

from src.codegen.ir import Operand, OperandKind
from src.codegen.names import LabelFactory, TemporaryPool
from src.semantic.types import BOOLEAN, INTEGER


def test_temporaries_recycle_only_after_release_and_track_peak():
    pool = TemporaryPool()
    first = pool.acquire(INTEGER)
    second = pool.acquire(INTEGER)
    assert first.value != second.value
    assert pool.active_count == 2
    assert pool.peak_active == 2

    pool.release(first)
    reused = pool.acquire(INTEGER)
    assert reused.value == first.value
    assert reused != first
    assert pool.active_count == 2
    assert pool.peak_active == 2


def test_temporary_pool_rejects_double_release_and_stale_use():
    pool = TemporaryPool()
    old = pool.acquire(INTEGER)
    pool.release(old)
    with pytest.raises(ValueError):
        pool.release(old)
    pool.acquire(INTEGER)
    with pytest.raises(ValueError):
        pool.validate(old)


def test_temporary_pool_rejects_foreign_and_non_temporary_operands():
    local = TemporaryPool()
    foreign = TemporaryPool().acquire(INTEGER)
    with pytest.raises(ValueError):
        local.release(foreign)
    with pytest.raises(TypeError):
        local.release(Operand(OperandKind.CONSTANT, 1, INTEGER))


def test_temporary_pool_does_not_reuse_incompatible_type():
    pool = TemporaryPool()
    integer = pool.acquire(INTEGER)
    pool.release(integer)
    boolean = pool.acquire(BOOLEAN)
    assert boolean.value != integer.value


def test_labels_are_unique_across_prefixes():
    factory = LabelFactory()
    first = factory.next("end")
    second = factory.next("end")
    third = factory.next("other")
    assert [first.value, second.value, third.value] == ["end0", "end1", "other2"]

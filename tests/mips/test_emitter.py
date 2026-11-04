"""CORE-01: invalid destinations cannot be published as assembly."""
import pytest


def test_core_01_deterministic_and_validated():
    from src.mips.emitter import MipsEmitter
    from src.mips.diagnostics import MipsError
    def emit():
        out = MipsEmitter()
        out.mark('main')
        target = out.label('fn.with punctuation')
        out.branch('b', target)
        out.mark(target)
        out.emit('li', '$v0', '10')
        out.emit('syscall')
        return out.render()
    assert emit() == emit()
    out = MipsEmitter()
    out.mark('main')
    with pytest.raises(MipsError, match='DUPLICATE'):
        out.mark('main')
    out.branch('b', 'missing')
    with pytest.raises(MipsError, match='LABEL'):
        out.render()


def test_core_01_assembles(mars):
    from src.mips.emitter import MipsEmitter
    from src.mips.simulator import run_mars
    out = MipsEmitter()
    out.mark('main')
    out.emit('li', '$v0', '10')
    out.emit('syscall')
    assert run_mars(out.render(), mars).accepted

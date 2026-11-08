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


def test_ascii_reuses_equal_strings():
    from src.mips.emitter import MipsEmitter
    out = MipsEmitter()
    assert out.ascii('true') == out.ascii('true') != out.ascii('false')
    assert len(out.data) == 2


def test_ascii_and_double_with_the_same_bytes_keep_separate_labels():
    import struct
    from src.mips.emitter import MipsEmitter
    out = MipsEmitter()
    bits = struct.unpack('<d', b'abcdefg\0')[0]
    assert out.double(bits) != out.ascii('abcdefg')


def test_non_ascii_text_is_a_backend_diagnostic():
    from src.mips.diagnostics import MipsError
    from src.mips.emitter import MipsEmitter
    with pytest.raises(MipsError, match='MIPS-NON-ASCII'):
        MipsEmitter().ascii('año')

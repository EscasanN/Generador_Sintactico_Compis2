"""MEM-01: checked machine addresses and widths."""
import pytest


@pytest.mark.parametrize('offset,size,width', [(1, 8, 4), (0, 2, 4), (-1, 8, 1),
    (0.0, 8, 4), (0, 8.5, 4), (0, 8, True)])
def test_mem_01_rejects_invalid_storage(offset, size, width):
    from src.mips.models import MachineLocation
    with pytest.raises(ValueError):
        MachineLocation('$fp', offset, size, width)


def test_mem_01_overlap():
    from src.mips.models import MachineLocation, validate_locations
    with pytest.raises(ValueError, match='overlap'):
        validate_locations([MachineLocation('$fp', 0, 8, 4), MachineLocation('$fp', 4, 8, 4)])


def test_mem_01_typed_storage(mars):
    from src.mips.emitter import MipsEmitter
    from src.mips.models import MachineLocation
    from src.mips.simulator import run_mars
    out = MipsEmitter()
    out.mark('main')
    out.emit('li', '$t8', '-8')
    out.emit('and', '$sp', '$sp', '$t8')
    out.emit('addiu', '$sp', '$sp', '-32')
    out.emit('move', '$fp', '$sp')
    for offset in range(0, 32, 4):
        out.emit('sw', '$zero', f'{offset}($fp)')
    out.emit('li', '$t0', '12345')
    out.store('$t0', MachineLocation('$fp', 4, 4, 4))
    out.emit('li', '$t0', '255')
    out.store('$t0', MachineLocation('$fp', 0, 1, 1))
    out.load('$a0', MachineLocation('$fp', 0, 1, 1))
    out.emit('li', '$v0', '1')
    out.emit('syscall')
    out.load('$a0', MachineLocation('$fp', 4, 4, 4))
    out.emit('syscall')
    out.emit('l.d', '$f2', out.double(3.75))
    out.store('$f2', MachineLocation('$fp', 8, 8, 8))
    out.load('$f12', MachineLocation('$fp', 8, 8, 8))
    out.emit('li', '$v0', '3')
    out.emit('syscall')
    # A pointer is a 32-bit word in an eight-byte reserved region.
    out.store('$fp', MachineLocation('$fp', 16, 8, 4))
    out.load('$t0', MachineLocation('$fp', 16, 8, 4))
    out.emit('seq', '$a0', '$t0', '$fp')
    out.emit('li', '$v0', '1')
    out.emit('syscall')
    out.emit('lw', '$a0', '20($fp)')
    out.emit('syscall')
    out.emit('li', '$v0', '10')
    out.emit('syscall')
    result = run_mars(out.render(), mars)
    assert result.accepted, result
    assert result.stdout == '255123453.7510'

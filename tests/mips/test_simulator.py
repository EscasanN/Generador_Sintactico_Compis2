"""SIM-01: exercise process outcomes, not a mocked simulator."""
from pathlib import Path

import pytest


HELLO = '.text\n.globl main\nmain:\nli $a0, 30\nli $v0, 1\nsyscall\nli $a0, 0\nli $v0, 17\nsyscall\n'


def test_sim_01_missing_tool(tmp_path):
    from src.mips.models import MarsConfig
    from src.mips.simulator import run_mars
    result = run_mars(HELLO, MarsConfig(tmp_path / 'missing.jar'))
    assert result.status == 'tool_error'
    assert result.diagnostics[0].code == 'MIPS-TOOL-MISSING'


@pytest.mark.parametrize('timeout,steps', [(0, 1), (1, 0), (-1, 2)])
def test_invalid_limits(timeout, steps):
    from src.mips.models import MarsConfig
    with pytest.raises(ValueError):
        MarsConfig(Path('mars.jar'), timeout=timeout, step_limit=steps)


def test_sim_01_execution_outcomes(mars):
    from src.mips.simulator import run_mars
    ok = run_mars(HELLO, mars)
    assert ok.accepted, ok
    assert ok.stdout == '30'
    assert ok.assembled and ok.returncode == 0
    bad = run_mars('.text\nmain:\nnot_an_instruction\n', mars)
    assert bad.status == 'assembly_error' and not bad.assembled
    trap = run_mars('.text\nmain:\nlw $t0, 1($zero)\n', mars)
    assert trap.status == 'simulation_error' and trap.assembled
    limit = run_mars('.text\nmain:\nj main\nnop\n', mars)
    assert limit.status == 'step_limit' and not limit.accepted


def test_sim_01_timeout(mars):
    from dataclasses import replace
    from src.mips.simulator import run_mars
    result = run_mars(HELLO, replace(mars, timeout=0.001))
    assert result.status == 'timeout' and not result.accepted


JAVAPATH = Path(r'C:\Program Files\Common Files\Oracle\Java\javapath\java.exe')


@pytest.mark.skipif(not JAVAPATH.is_file(), reason='needs the Oracle javapath launcher')
def test_timeout_terminates_the_java_child_of_a_launcher(mars):
    """INC-B4-01: the launcher's real java.exe child must die with the timeout."""
    import time
    from dataclasses import replace
    from src.mips.simulator import run_mars
    started = time.monotonic()
    result = run_mars('.text\nmain:\nj main\nnop\n',
                      replace(mars, java=str(JAVAPATH), timeout=2, step_limit=10**9))
    assert result.status == 'timeout'
    assert time.monotonic() - started < 30


def test_timeout_keeps_output_already_printed(mars):
    from dataclasses import replace
    from src.mips.simulator import run_mars
    source = HELLO.replace('li $a0, 0', 'li $a0, 10000\nli $v0, 32\nsyscall\nli $a0, 0')
    result = run_mars(source, replace(mars, timeout=3.0))
    assert result.status == 'timeout' and result.assembled
    assert result.stdout == '30'

"""The handoff example must be executable without importing test helpers."""
import subprocess
import sys


def test_handoff_example_exports_and_executes(mars, tmp_path):
    target = tmp_path / 'example.asm'
    run = subprocess.run([sys.executable, '-m', 'scripts.demo_mips_core',
                          '--jar', str(mars.jar), '--output', str(target)],
                         capture_output=True, text=True, encoding='utf-8', timeout=20)
    assert run.returncode == 0, run.stderr
    assert run.stdout == '30\n'
    assert target.is_file()

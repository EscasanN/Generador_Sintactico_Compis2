"""Explicit, bounded MARS processes. Importing this module has no side effects."""
import os
import subprocess
import tempfile
from pathlib import Path

from src.mips.diagnostics import MipsDiagnostic
from src.mips.models import MarsConfig, MipsExecutionResult


def run_mars(assembly: str, config: MarsConfig) -> MipsExecutionResult:
    if not config.jar.is_file():
        return MipsExecutionResult('tool_error', diagnostics=(
            MipsDiagnostic('MIPS-TOOL-MISSING', str(config.jar), phase='tool'),))
    assembled = False
    stdout = stderr = ''
    try:
        with tempfile.TemporaryDirectory(prefix='compiscript-mars-') as directory:
            path = Path(directory) / 'program.asm'
            path.write_text(assembly, encoding='utf-8', newline='\n')
            command = [config.java, '-Dfile.encoding=UTF-8', '-jar', str(config.jar.resolve()),
                       'nc', 'me', 'ae2', 'se3']
            for assemble_only in (True, False):
                options = ['a'] if assemble_only else ['sm', str(config.step_limit)]
                if config.delayed_branching:
                    options.append('db')
                completed = subprocess.run(
                    [*command, *options, str(path)], capture_output=True, text=True,
                    encoding='utf-8', errors='replace', timeout=config.timeout, check=False,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                )
                stdout, stderr = completed.stdout.replace('\r\n', '\n'), completed.stderr.replace('\r\n', '\n')
                if assemble_only:
                    if completed.returncode != 0:
                        return _failure('assembly_error', False, stdout, stderr, completed.returncode)
                    assembled = True
                elif 'maximum step limit' in stderr.lower():
                    return _failure('step_limit', True, stdout, stderr, completed.returncode)
                elif completed.returncode == 3:
                    return _failure('simulation_error', True, stdout, stderr, completed.returncode)
                elif completed.returncode:
                    return _failure('runtime_error', True, stdout, stderr, completed.returncode)
            return MipsExecutionResult('success', True, stdout, stderr, 0)
    except subprocess.TimeoutExpired as error:
        # subprocess.run kills and waits for its direct Java child before raising.
        return _failure('timeout', assembled, _text(error.output), _text(error.stderr), None)
    except OSError as error:
        return MipsExecutionResult('tool_error', assembled, diagnostics=(
            MipsDiagnostic('MIPS-TOOL-MISSING', str(error), phase='tool'),))


def _text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        value = value.decode('utf-8', errors='replace')
    return (value or '').replace('\r\n', '\n')


def _failure(status: str, assembled: bool, stdout: str, stderr: str,
             returncode: int | None) -> MipsExecutionResult:
    code = {'assembly_error': 'MIPS-ASSEMBLY-ERROR', 'simulation_error': 'MIPS-SIMULATION-ERROR',
            'step_limit': 'MIPS-STEP-LIMIT', 'timeout': 'MIPS-TIMEOUT',
            'runtime_error': 'MIPS-RUNTIME-ERROR'}[status]
    return MipsExecutionResult(status, assembled, stdout, stderr, returncode,
                               (MipsDiagnostic(code, stderr or status, phase='execution'),))

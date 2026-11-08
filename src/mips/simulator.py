"""Explicit, bounded MARS processes. Importing this module has no side effects."""
import os
import signal
import subprocess
import tempfile
import threading
import time
from collections.abc import Sequence
from pathlib import Path

from src.mips.diagnostics import MipsDiagnostic
from src.mips.models import MarsConfig, MipsExecutionResult

CANCELLED = 'cancelled'


def run_mars(assembly: str, config: MarsConfig) -> MipsExecutionResult:
    return CancellableMarsRun(assembly, config).run()


def _kill_tree(process: subprocess.Popen) -> None:
    """Terminate ``process`` and its children.

    On Windows ``java`` is often the ``javapath`` launcher, which starts the real
    ``java.exe`` as a child that keeps the pipes open: killing only the launcher
    would leave the simulation running. ``taskkill /T`` must run while the
    launcher is still alive so the tree can be found.
    """
    if process.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)],
                       capture_output=True, check=False,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    if process.poll() is None:
        process.kill()


class CancellableMarsRun:
    """One MARS execution (assemble, then simulate) that another thread may cancel.

    A cancelled run reports status ``cancelled`` with ``MIPS-CANCELLED``; a
    timeout or a cancellation terminates the whole Java process tree.
    """

    POLL_SECONDS = 0.05

    def __init__(self, assembly: str, config: MarsConfig) -> None:
        self.assembly = assembly
        self.config = config
        self._cancelled = threading.Event()
        self._lock = threading.Lock()
        self._process: subprocess.Popen | None = None

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def cancel(self) -> None:
        """Request cancellation; terminates the running Java process if any."""
        self._cancelled.set()
        with self._lock:
            process = self._process
        if process is not None:
            _kill_tree(process)

    def run(self) -> MipsExecutionResult:
        config = self.config
        if not config.jar.is_file():
            return MipsExecutionResult('tool_error', diagnostics=(
                MipsDiagnostic('MIPS-TOOL-MISSING', str(config.jar), phase='tool'),))
        assembled = False
        stdout = stderr = ''
        try:
            with tempfile.TemporaryDirectory(prefix='compiscript-mars-') as directory:
                path = Path(directory) / 'program.asm'
                path.write_text(self.assembly, encoding='utf-8', newline='\n')
                command = [config.java, '-Dfile.encoding=UTF-8', '-jar',
                           str(config.jar.resolve()), 'nc', 'me', 'ae2', 'se3']
                for assemble_only in (True, False):
                    options = ['a'] if assemble_only else ['sm', str(config.step_limit)]
                    if config.delayed_branching:
                        options.append('db')
                    outcome = self._invoke([*command, *options, str(path)])
                    if outcome is None:
                        return self._cancelled_result(assembled, stdout, stderr)
                    returncode, stdout, stderr = outcome
                    if assemble_only:
                        if returncode != 0:
                            return _failure('assembly_error', False, stdout, stderr, returncode)
                        assembled = True
                    elif 'maximum step limit' in stderr.lower():
                        return _failure('step_limit', True, stdout, stderr, returncode)
                    elif returncode == 3:
                        return _failure('simulation_error', True, stdout, stderr, returncode)
                    elif returncode:
                        return _failure('runtime_error', True, stdout, stderr, returncode)
                return MipsExecutionResult('success', True, stdout, stderr, 0)
        except subprocess.TimeoutExpired as error:
            return _failure('timeout', assembled, _text(error.output), _text(error.stderr), None)
        except OSError as error:
            return MipsExecutionResult('tool_error', assembled, diagnostics=(
                MipsDiagnostic('MIPS-TOOL-MISSING', str(error), phase='tool'),))

    def _invoke(self, arguments: Sequence[str]) -> tuple[int, str, str] | None:
        """Run one MARS command; ``None`` when cancelled. The process is always reaped."""
        if self.cancelled:
            return None
        process = subprocess.Popen(
            list(arguments), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding='utf-8', errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            start_new_session=os.name != 'nt',
        )
        with self._lock:
            self._process = process
        try:
            if self.cancelled:
                _kill_tree(process)
            started = time.monotonic()
            while True:
                try:
                    out, err = process.communicate(timeout=self.POLL_SECONDS)
                    break
                except subprocess.TimeoutExpired:
                    if self.cancelled:
                        _kill_tree(process)
                    elif time.monotonic() - started >= self.config.timeout:
                        _kill_tree(process)
                        out, err = process.communicate()
                        raise subprocess.TimeoutExpired(arguments, self.config.timeout,
                                                        output=out, stderr=err) from None
        finally:
            if process.poll() is None:
                _kill_tree(process)
                process.communicate()
            with self._lock:
                self._process = None
        if self.cancelled:
            return None
        return process.returncode, _text(out), _text(err)

    def _cancelled_result(self, assembled: bool, stdout: str, stderr: str) -> MipsExecutionResult:
        return MipsExecutionResult(CANCELLED, assembled, stdout, stderr, None, (
            MipsDiagnostic('MIPS-CANCELLED', 'ejecución cancelada por el usuario',
                           phase='execution'),))


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

"""A rejected frontend or generation must never become an accepted wrapper."""
import pytest


def test_results_preserve_phase_gates():
    from src.codegen.pipeline import compile_compiscript
    from src.mips.models import MipsCompilationResult, MipsGenerationResult
    from src.mips.diagnostics import MipsDiagnostic
    frontend = compile_compiscript('let x: integer = 1;')
    assert frontend.accepted
    assert MipsCompilationResult(frontend).failed_stage == 'mips'
    assert MipsCompilationResult(frontend, MipsGenerationResult('complete')).accepted
    rejected = compile_compiscript('let x: integer = true;')
    assert MipsCompilationResult(rejected).failed_stage == 'semantic'
    with pytest.raises(ValueError):
        MipsCompilationResult(rejected, MipsGenerationResult('partial'))
    with pytest.raises(ValueError):
        MipsGenerationResult('partial', (MipsDiagnostic('MIPS-INVALID-IR', 'bad IR'),))


def test_execution_diagnostics_do_not_retain_mutable_input():
    from src.mips.models import MipsExecutionResult
    diagnostics = []
    result = MipsExecutionResult('tool_error', diagnostics=diagnostics)
    diagnostics.append('changed')
    assert not result.diagnostics

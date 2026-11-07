"""Integral API: Compiscript source to MIPS assembly (block 3).

``compile_to_mips`` runs the existing ``compile_compiscript`` unchanged and only
calls the backend when syntax, semantics and TAC were all accepted, so a
rejection of an earlier phase never produces assembly.  It neither assembles
nor executes the program: running it in MARS is the explicit, separate action
``run_mips`` (or ``src.mips.simulator.run_mars``).
"""
from __future__ import annotations

from pathlib import Path

from src.codegen.pipeline import compile_compiscript
from src.mips.generator import generate_mips
from src.mips.models import MarsConfig, MipsCompilationResult, MipsExecutionResult
from src.mips.simulator import run_mars


def compile_to_mips(source: str, source_path: str | Path | None = None) -> MipsCompilationResult:
    """Compile ``source``; the result keeps the whole frontend result and the MIPS one."""
    frontend = compile_compiscript(source, source_path)
    if not frontend.accepted:
        return MipsCompilationResult(frontend, None)
    return MipsCompilationResult(frontend, generate_mips(frontend.intermediate_result))


def run_mips(compilation: MipsCompilationResult, config: MarsConfig) -> MipsExecutionResult:
    """Execute an accepted compilation in MARS; a rejected one is never run."""
    if not compilation.accepted or compilation.mips is None:
        raise ValueError('only an accepted MIPS compilation can be executed')
    return run_mars(compilation.mips.assembly, config)

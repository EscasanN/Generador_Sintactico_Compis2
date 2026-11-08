"""Helpers for the block 3 tests: real compiler, complete backend and MARS.

Expected outputs are always literals written by hand next to each program or
in the JSON oracles of ``tests/cps/mips/esperados``; nothing here derives an
oracle from the backend under test.
"""
from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

from src.codegen.ir import IRProgram, Instruction
from src.codegen.results import IntermediateCodeResult
from src.mips.generator import MipsProgramEmitter, generate_mips
from src.mips.layout import PhysicalLayoutPlan
from src.mips.pipeline import compile_to_mips
from src.mips.simulator import run_mars

FIXTURES = Path(__file__).resolve().parents[1] / 'cps' / 'mips'
ORACLES = FIXTURES / 'esperados'
HEADER = re.compile(r'^// IDs: (?P<ids>.+)\n// Esperado: (?P<expected>.+)$', re.MULTILINE)


def fixture_paths() -> list[Path]:
    return sorted(path for folder in ('validos', 'runtime', 'invalidos')
                  for path in (FIXTURES / folder).glob('*.cps'))


def fixture_header(path: Path) -> tuple[list[str], str]:
    match = HEADER.search(path.read_text(encoding='utf-8'))
    assert match, f'{path.name} needs // IDs and // Esperado headers'
    return [item.strip() for item in match['ids'].split(',')], match['expected'].strip()


def oracle(path: Path) -> dict:
    return json.loads((ORACLES / f'{path.stem}.json').read_text(encoding='utf-8'))


def intermediate(source: str) -> IntermediateCodeResult:
    result = compile_to_mips(source)
    assert result.frontend.accepted, result.frontend.failed_stage
    return result.frontend.intermediate_result


def run_source(source: str, mars, *, gpr_count: int = 8, fpr_count: int = 5, expect_success=True):
    """Compile with the complete backend and execute; returns the MARS result."""
    generated = generate_mips(intermediate(source), gpr_count=gpr_count, fpr_count=fpr_count)
    assert generated.accepted, generated.diagnostics
    result = run_mars(generated.assembly, mars)
    if expect_success:
        assert result.accepted, (result.status, result.stdout, result.stderr[-400:])
    return result


def output(source: str, mars, **options) -> list[str]:
    return run_source(source, mars, **options).stdout.split('\n')[:-1]


def assemble_with_hooks(source: str, before_global=None, after_global=None, **options) -> str:
    """Complete backend plus raw global hooks (stack and ``$s`` canaries)."""
    ir = intermediate(source)
    plan = PhysicalLayoutPlan.build(ir.program, ir.layouts)
    return MipsProgramEmitter(plan, **options).assemble(
        ir.program, before_global=before_global, after_global=after_global)


def with_program(result: IntermediateCodeResult, program: IRProgram) -> IntermediateCodeResult:
    """An accepted TAC result whose structured program was replaced (manual IR)."""
    return IntermediateCodeResult(program, result.text, (), result.layouts, result.statistics)


def mutate(result: IntermediateCodeResult, predicate, change) -> IntermediateCodeResult:
    """Replace the first instruction matching ``predicate`` with ``change(instruction)``."""
    done = False

    def rewrite(items: tuple[Instruction, ...]) -> tuple[Instruction, ...]:
        nonlocal done
        rewritten = []
        for item in items:
            if not done and predicate(item):
                item, done = change(item), True
            rewritten.append(item)
        return tuple(rewritten)

    program = result.program
    global_code = rewrite(program.global_code)
    procedures = tuple(dataclasses.replace(p, instructions=rewrite(p.instructions))
                       for p in program.procedures)
    assert done, 'no instruction matched the mutation'
    return with_program(result, IRProgram(global_code, procedures))


__all__ = ['FIXTURES', 'assemble_with_hooks', 'fixture_header', 'fixture_paths',
           'intermediate', 'mutate', 'oracle', 'output', 'run_source', 'with_program']

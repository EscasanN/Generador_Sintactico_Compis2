"""PIPE-01 and PIPE-02: the integral API ``.cps`` -> MIPS and handler coverage."""
import dataclasses
from pathlib import Path

import pytest

from pipeline_harness import (
    FIXTURES, fixture_header, fixture_paths, intermediate, mutate, oracle, with_program,
)
from src.codegen.ir import IRProgram, Instruction, OpCode, Operand, OperandKind
from src.codegen.pipeline import compile_compiscript
from src.codegen.results import IntermediateCodeResult
from src.codegen.verifier import IRDiagnostic
from src.mips import generator as generator_module
from src.mips import pipeline as pipeline_module
from src.mips.generator import MipsProgramEmitter, generate_mips
from src.mips.layout import PhysicalLayoutPlan
from src.mips.lists import ListHandler
from src.mips.models import MipsCompilationResult
from src.mips.pipeline import compile_to_mips, run_mips
from src.mips.simulator import run_mars

CPS = Path(__file__).resolve().parents[1] / 'cps'
REQUIRED_IDS = {'STR-01', 'LIST-01', 'OBJ-01', 'OBJ-02', 'OBJ-03', 'EXC-01', 'EXC-02', 'EXC-03',
                'PIPE-01'}
PROJECT_PROGRAMS = sorted([*(CPS / 'validos').glob('*.cps'), *(CPS / 'codegen' / 'validos').glob('*.cps'),
                           *(CPS / 'advertencias').glob('*.cps'), CPS / 'demostracion-valida.cps'])


# -- INC-B3-01: break/continue that skip the join of an if or a switch ---------------------

LEAVE_JOIN = '''
let n: integer = 0;
for (;;) { n = n + 1; if (n == 4) { break; } }
print(n);
let s: integer = 0;
for (;;) { s = s + 1; switch (s == 3) { case true: break; default: print(s); } }
print(s * 10);
let c: integer = 0;
let k: integer = 0;
for (; k < 5; k = k + 1) { if (k % 2 == 0) { continue; } c = c + k; }
let w: integer = 0;
while (w < 2) { w = w + 1; }
print(c + w);
'''


@pytest.mark.parametrize('gpr_count', [8, 2])
def test_inc_b3_01_break_and_continue_release_values_held_until_a_join(mars, gpr_count):
    from pipeline_harness import output
    assert output(LEAVE_JOIN, mars, gpr_count=gpr_count) == ['4', '1', '2', '30', '6']


# -- PIPE-01: fixtures by domain ---------------------------------------------------------

def test_pipe_01_fixture_inventory():
    paths = fixture_paths()
    stems = [path.stem for path in paths]
    assert len(stems) == len(set(stems)), 'fixture basenames must be unique'
    oracles = {path.stem for path in (FIXTURES / 'esperados').glob('*.json')}
    assert oracles == set(stems), 'every fixture needs exactly one oracle and vice versa'
    covered = {identifier for path in paths for identifier in fixture_header(path)[0]}
    assert REQUIRED_IDS <= covered
    for path in paths:
        expected = fixture_header(path)[1].split()
        folder = path.parent.name
        assert {'validos': 'ACCEPT', 'runtime': 'RUNTIME', 'invalidos': 'REJECT'}[folder] == expected[0]


@pytest.mark.parametrize('path', fixture_paths(), ids=lambda p: p.stem)
def test_pipe_01_end_to_end(mars, path):
    _, header = fixture_header(path)
    expected = oracle(path)
    compiled = compile_to_mips(path.read_text(encoding='utf-8'), path)
    assert compiled.accepted == expected['compile']['accepted'], compiled.failed_stage
    if not compiled.accepted:
        kind, stage, *code = header.split()
        assert kind == 'REJECT' and compiled.failed_stage == stage == expected['compile']['stage']
        assert compiled.mips is None, 'an earlier phase failed: the backend must not run'
        if code:
            diagnostics = compiled.frontend.intermediate_result.diagnostics
            assert [d.code for d in diagnostics][:1] == code == [expected['compile']['code']]
        assert expected['execution'] is None
        return
    assert compiled.mips.diagnostics == ()
    execution = expected['execution']
    result = run_mars(compiled.mips.assembly, mars)
    assert result.assembled
    assert result.returncode == execution['exit_code'], (result.status, result.stderr[-300:])
    assert result.stdout == execution['stdout']
    if execution['runtime_code'] is None:
        assert header == 'ACCEPT' and result.status == 'success'
    else:
        assert header == f"RUNTIME {execution['runtime_code']}"
        assert result.status == 'runtime_error'
        assert result.stdout.endswith(f"RuntimeError: {execution['runtime_code']}\n")


@pytest.mark.parametrize('path', PROJECT_PROGRAMS, ids=lambda p: f'{p.parent.name}/{p.stem}')
def test_pipe_01_every_accepted_project_program_generates_mips(path):
    """Warnings never block; every valid program of earlier phases translates cleanly."""
    compiled = compile_to_mips(path.read_text(encoding='utf-8'), path)
    assert compiled.accepted, compiled.mips.diagnostics if compiled.mips else compiled.failed_stage
    assert compiled.mips.diagnostics == () and compiled.mips.assembly.startswith('.data')


def test_pipe_01_rejected_phases_never_call_the_backend(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError('the backend ran after a rejected phase')
    monkeypatch.setattr(pipeline_module, 'generate_mips', forbidden)
    for path in sorted((FIXTURES / 'invalidos').glob('*.cps')):
        compiled = compile_to_mips(path.read_text(encoding='utf-8'), path)
        assert not compiled.accepted and compiled.mips is None
        assert compiled.failed_stage in ('syntax', 'semantic', 'codegen')
        assert compiled.frontend.tac == ''


def test_pipe_01_frontend_result_is_preserved_and_nothing_is_executed(monkeypatch):
    source = (CPS / 'codegen' / 'validos' / 'FUN-01-funciones.cps').read_text(encoding='utf-8')
    monkeypatch.setattr(pipeline_module, 'run_mars', lambda *_: pytest.fail('compile ran MARS'))
    compiled = compile_to_mips(source)
    assert compiled.accepted and compiled.failed_stage is None
    assert compiled.frontend.tac == compile_compiscript(source).tac
    assert compiled.mips.layouts is not None
    statistics = compiled.mips.statistics
    assert statistics['instructions'] > 0 and statistics['frames'] >= 2
    with pytest.raises(dataclasses.FrozenInstanceError):
        compiled.mips.assembly = ''
    with pytest.raises(TypeError):
        statistics['spills'] = 0


def test_pipe_01_run_mips_executes_only_accepted_compilations(mars):
    compiled = compile_to_mips('print("hola");\n')
    assert run_mips(compiled, mars).stdout == 'hola\n'
    rejected = compile_to_mips('let x: integer = "no";\n')
    assert rejected.failed_stage == 'semantic'
    with pytest.raises(ValueError):
        run_mips(rejected, mars)


# -- PIPE-02: coverage and contracts -----------------------------------------------------

def _emitter() -> MipsProgramEmitter:
    ir = intermediate('print(1);\n')
    return MipsProgramEmitter(PhysicalLayoutPlan.build(ir.program, ir.layouts))


def test_opcode_catalog_is_complete():
    """Compares the real enum, not a list copied into this test."""
    emitter = _emitter()
    for opcode in OpCode:
        owners = emitter.handler_for(opcode)
        assert len(owners) == 1, f'{opcode.value} has {len(owners)} handlers'


def test_pipe_02_rejections():
    ir = intermediate('let xs: integer[] = [1, 2];\nfunction f(): integer { return 1; }\nprint(f());\n')
    # unsupported opcode: a composition missing the list handler is rejected, never a nop
    emitter = MipsProgramEmitter(PhysicalLayoutPlan.build(ir.program, ir.layouts))
    emitter.handlers = [h for h in emitter.handlers if not isinstance(h, ListHandler)]
    with pytest.raises(generator_module.MipsError) as caught:
        emitter.assemble(ir.program)
    assert caught.value.diagnostic.code == 'MIPS-UNSUPPORTED-OPCODE'
    assert caught.value.diagnostic.location is not None
    # unknown external label
    unknown = mutate(ir, lambda i: i.opcode is OpCode.CALL and i.arg1.value != 'print',
                     lambda i: Instruction(OpCode.CALL, Operand(OperandKind.LABEL, 'externa'),
                                           i.arg2, i.result, i.source_location))
    generated = generate_mips(unknown)
    assert [d.code for d in generated.diagnostics] == ['MIPS-UNKNOWN-EXTERNAL']
    assert generated.diagnostics[0].location is not None and generated.assembly == ''


def test_pipe_02_invalid_inputs_are_rejected_without_assembly():
    rejected = IntermediateCodeResult.rejected((IRDiagnostic('IRGEN-X', 'falló'),))
    assert [d.code for d in generate_mips(rejected).diagnostics] == ['MIPS-INVALID-IR']
    assert [d.code for d in generate_mips(object()).diagnostics] == ['MIPS-INVALID-IR']
    ir = intermediate('print(1);\n')
    without_layouts = IntermediateCodeResult(ir.program, ir.text, (), None, ir.statistics)
    assert [d.code for d in generate_mips(without_layouts).diagnostics] == ['MIPS-MISSING-LAYOUT']
    # a malformed client program is verified again by the backend (jump to a missing label)
    broken = with_program(ir, IRProgram((*ir.program.global_code,
                                         Instruction(OpCode.GOTO, result=Operand(OperandKind.LABEL, 'L99'))),
                                        ir.program.procedures))
    generated = generate_mips(broken)
    assert [d.code for d in generated.diagnostics] == ['MIPS-INVALID-IR'] and generated.assembly == ''


def test_pipe_02_compilation_result_keeps_stages():
    failed = compile_to_mips('let y: integer = ;\n')
    assert isinstance(failed, MipsCompilationResult)
    assert failed.failed_stage == 'syntax' and failed.mips is None and not failed.accepted
    accepted = compile_to_mips('print(1);\n')
    assert accepted.accepted and accepted.mips.accepted and accepted.frontend.accepted

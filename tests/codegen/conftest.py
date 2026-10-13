"""Shared helpers: analyze real Compiscript source, index its codegen facts and lower it."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pytest

from src.codegen.ir import IRProgram
from src.codegen.semantic_facts import SemanticFactsIndex
from src.semantic.antlr_adapter import analyze_semantics_with_g4

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAMMAR = REPO_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
PROFILE = REPO_ROOT / "semantic_profiles" / "compiscript.semantic.json"


@lru_cache(maxsize=None)
def _compile(source: str, with_tree: bool):
    run = analyze_semantics_with_g4(GRAMMAR, source, PROFILE, "program")
    assert run.accepted, run.semantic_result and run.semantic_result.diagnostics
    root = run.syntax_result.tree if with_tree else None
    return run, SemanticFactsIndex.from_result(run.semantic_result, root)


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def references(root, name):
    """Identifier-expression nodes naming ``name``, in source order."""
    return [
        node
        for node in walk(root)
        if node.alternative == "IdentifierExpr"
        and any(child.text == name for child in node.children)
    ]


@pytest.fixture
def compile_facts():
    """``compile_facts(source, with_tree=True) -> (SemanticRunResult, SemanticFactsIndex)``."""
    return lambda source, with_tree=True: _compile(source, with_tree)


@pytest.fixture
def find_references():
    return references


@pytest.fixture
def walk_tree():
    return walk


@dataclass(frozen=True)
class Lowered:
    """A whole program lowered by the block-3 generator and already verified."""

    run: object
    facts: SemanticFactsIndex
    program: IRProgram
    layouts: object
    text: str

    def unit(self, label: str = "global") -> tuple:
        """Instructions of global code or of the procedure labelled ``label``."""
        if label == "global":
            return self.program.global_code
        return next(p for p in self.program.procedures if p.label.value == label).instructions


@pytest.fixture
def generate_tac(compile_facts):
    """``generate_tac(source) -> Lowered``; the IR must pass ``IRVerifier``."""
    from src.codegen.formatter import format_program
    from src.codegen.generator import CompiscriptCodeGenerator
    from src.codegen.verifier import IRVerifier

    def lower(source: str) -> Lowered:
        run, facts = compile_facts(source)
        generated = CompiscriptCodeGenerator(facts).generate(run.syntax_result.tree)
        diagnostics = IRVerifier().verify(generated.program)
        assert diagnostics == (), diagnostics
        return Lowered(
            run, facts, generated.program, generated.layouts, format_program(generated.program)
        )

    return lower

"""Shared helpers: analyze real Compiscript source and index its codegen facts."""

from functools import lru_cache
from pathlib import Path

import pytest

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

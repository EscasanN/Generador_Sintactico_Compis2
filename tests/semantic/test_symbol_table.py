from src.semantic.diagnostics import SourceLocation
from src.semantic.symbol_table import ScopeKind, Symbol, SymbolKind, SymbolTable
from src.semantic.types import BOOLEAN, INTEGER


LOC = SourceLocation(1, 1)


def symbol(name: str, type_=INTEGER) -> Symbol:
    return Symbol(name, SymbolKind.VARIABLE, type_, True, LOC)


def test_scp_01_success_resolves_nearest_local_then_global_symbol():
    table = SymbolTable(location=LOC)
    global_x = symbol("x")
    assert table.declare(global_x)
    table.enter_scope(ScopeKind.BLOCK, "inner", LOC)
    local_x = symbol("x", BOOLEAN)
    assert table.declare(local_x)
    assert table.resolve("x") is local_x
    table.exit_scope()
    assert table.resolve("x") is global_x


def test_scp_01_failure_returns_none_for_an_undeclared_name():
    assert SymbolTable().resolve("missing") is None


def test_scp_02_success_allows_shadowing_in_a_child_scope():
    table = SymbolTable()
    assert table.declare(symbol("value"))
    table.enter_scope(ScopeKind.BLOCK, "child", LOC)
    assert table.declare(symbol("value", BOOLEAN))


def test_scp_02_failure_rejects_redeclaration_in_the_same_scope():
    table = SymbolTable()
    assert table.declare(symbol("value"))
    assert not table.declare(symbol("value", BOOLEAN))
    assert table.current_scope.resolve_local("value").type == INTEGER


def test_scp_03_success_child_scope_accesses_ancestor_and_closed_scope_is_hidden():
    table = SymbolTable()
    outer = symbol("outer")
    assert table.declare(outer)
    table.enter_scope(ScopeKind.BLOCK, "child", LOC)
    inner = symbol("inner")
    assert table.declare(inner)
    assert table.resolve("outer") is outer
    table.exit_scope()
    assert table.resolve("inner") is None


def test_scp_03_failure_sibling_scope_cannot_access_closed_sibling_name():
    table = SymbolTable()
    table.enter_scope(ScopeKind.BLOCK, "left", LOC)
    table.declare(symbol("private"))
    table.exit_scope()
    table.enter_scope(ScopeKind.BLOCK, "right", LOC)
    assert table.resolve("private") is None


def test_scp_04_success_preserves_global_function_class_and_block_scopes():
    table = SymbolTable()
    table.enter_scope(ScopeKind.FUNCTION, "f", LOC)
    table.enter_scope(ScopeKind.BLOCK, "body", LOC)
    table.exit_scope()
    table.exit_scope()
    table.enter_scope(ScopeKind.CLASS, "C", LOC)
    table.exit_scope()
    assert [scope.kind for scope in table.iter_scopes()] == [
        ScopeKind.GLOBAL,
        ScopeKind.FUNCTION,
        ScopeKind.BLOCK,
        ScopeKind.CLASS,
    ]
    assert all(scope.closed for scope in tuple(table.iter_scopes())[1:])


def test_scp_04_failure_cannot_reuse_global_as_a_child_or_exit_it():
    table = SymbolTable()
    try:
        table.enter_scope(ScopeKind.GLOBAL, "second", LOC)
    except ValueError:
        pass
    else:
        raise AssertionError("a second global scope was accepted")
    try:
        table.exit_scope()
    except RuntimeError:
        pass
    else:
        raise AssertionError("the global scope was closed")

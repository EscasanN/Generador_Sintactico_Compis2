import importlib
from sql_interpreter.frontend import parse_sql


def build(sql):
    return importlib.import_module('sql_interpreter.ast').build_ast(parse_sql(sql))


def test_ast_is_sql_structure_and_preserves_precedence():
    script = build('SELECT a+2*3 AS n FROM t WHERE a=1 OR b=2 AND c=3;')
    select = script.statements[0]
    assert select.kind == 'select'
    assert select.items[0].expr.op == '+'
    assert select.items[0].expr.right.op == '*'
    assert select.where.op == 'OR'
    assert select.where.right.op == 'AND'
    assert select.items[0].alias == 'n'
    assert select.location.line == 1


def test_ast_contains_nested_select_and_constraints():
    script = build('CREATE TABLE t (id INT PRIMARY KEY); SELECT * FROM t WHERE id IN (SELECT id FROM t);')
    assert script.statements[0].columns[0].constraints == ('PRIMARY KEY',)
    assert script.statements[1].where.query.kind == 'select'

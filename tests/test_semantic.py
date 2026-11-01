import pytest
from sql_interpreter.api import analyze_sql


@pytest.mark.parametrize('sql',[
    'CREATE TABLE t(id INT,id FLOAT);',
    'CREATE TABLE t(id VARCHAR(0));',
    'CREATE TABLE t(id INT PRIMARY KEY,n INT PRIMARY KEY);',
    'CREATE TABLE t(id INT); CREATE INDEX ix ON t(id); CREATE INDEX ix ON t(id);',
    'CREATE TABLE t(id INT); SELECT * FROM t a INNER JOIN t a ON a.id=a.id;',
    'CREATE TABLE t(id INT); SELECT SUM(COUNT(id)) FROM t;',
    'CREATE TABLE t(id INT); SELECT * FROM t WHERE COUNT(*)>1;',
    'CREATE TABLE t(id INT); INSERT INTO t VALUES(TRUE);',
    'CREATE TABLE t(id BOOLEAN); INSERT INTO t VALUES(1);',
    'CREATE TABLE t(id INT); SELECT * FROM t WHERE EXISTS(SELECT bad FROM t);',
])
def test_semantic_failures_are_located_without_gui_or_storage(sql):
    result = analyze_sql(sql)
    assert not result.accepted
    assert result.diagnostics[0].stage == 'SEMANTIC'
    assert result.diagnostics[0].location.line == 1


def test_nested_alias_shadowing_is_lexical():
    sql = 'CREATE TABLE t(id INT); SELECT * FROM t a WHERE EXISTS(SELECT * FROM t a WHERE a.id=1);'
    assert analyze_sql(sql).accepted

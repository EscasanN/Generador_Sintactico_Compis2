import importlib

import pytest


VALID = [
    "CREATE TABLE t (id INT PRIMARY KEY, n VARCHAR(20) NOT NULL, f FLOAT, b BOOLEAN, d DATE);",
    "DROP TABLE t; CREATE INDEX ix ON t(id); DROP INDEX ix;",
    "INSERT INTO t (id,n) VALUES (1,'O''Brien'), (2,NULL);",
    "UPDATE t SET n='x', id=id+1 WHERE id=2; DELETE FROM t WHERE id<0;",
    "SELECT t.*, n AS nombre FROM t WHERE NOT (id<2 OR id>5) AND n IS NOT NULL ORDER BY id DESC;",
    "SELECT a.id, COUNT(*), SUM(b.f), AVG(b.f), MIN(b.f), MAX(b.f) FROM t a INNER JOIN t b ON a.id=b.id GROUP BY a.id HAVING COUNT(*)>1;",
    "SELECT id FROM t WHERE id NOT IN (SELECT id FROM t) OR NOT EXISTS (SELECT * FROM t x WHERE x.id=t.id);",
    "SELECT id FROM t WHERE id >= (SELECT MAX(id) FROM t);",
    "-- comentario\nselect * from t /* bloque */ where d=DATE '2026-10-30'",
    "", 
]
INVALID = ["SELECT FROM t;", "SELECT * FROM;", "CREATE TABLE t (id);", "SELECT * FROM t garbage extra;", "SELECT * FROM t WHERE id IN ();", "SELECT * FROM t WHERE @;", "INSERT INTO t VALUES ('sin cerrar);", "/* sin cerrar",
    "DROP TABLE;", "CREATE INDEX ix ON t();", "DROP INDEX;", "INSERT t VALUES(1);",
    "UPDATE t SET WHERE id=1;", "DELETE t;", "SELECT * FROM a INNER JOIN b;",
    "SELECT COUNT() FROM t;", "SELECT id FROM t GROUP BY;", "SELECT id FROM t HAVING;",
    "SELECT * FROM t ORDER BY;", "SELECT * FROM t WHERE EXISTS SELECT * FROM t;",
    "SELECT * FROM t WHERE id=(SELECT FROM t);", "SELECT * FROM t WHERE id=1 AND;"
]


def parse(sql):
    module = importlib.import_module('sql_interpreter.frontend')
    return module.parse_sql(sql)


@pytest.mark.parametrize('sql', VALID)
def test_accepts_required_constructions(sql):
    result = parse(sql)
    assert result.accepted, result.diagnostics
    assert result.tree.rule_name == 'script'


@pytest.mark.parametrize('sql', INVALID)
def test_rejects_invalid_constructions(sql):
    result = parse(sql)
    assert not result.accepted
    assert all(d.location.line >= 1 and d.location.column >= 1 for d in result.diagnostics)


def test_tokens_preserve_text_and_one_based_location():
    result = parse("\nSELECT 'Hola' FROM t;")
    assert [(t.text, t.location.line, t.location.column) for t in result.tokens[:2]] == [('SELECT',2,1),("'Hola'",2,8)]
    assert result.tokens[0].token_type == 'SELECT'

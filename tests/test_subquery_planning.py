import pytest
from sql_interpreter.api import analyze_sql, execute_sql
from sql_interpreter.storage import FileStorage


def run(db,sql):
    r = execute_sql(sql,db)
    assert r.accepted,r.diagnostics
    return r.results[-1]


@pytest.fixture
def db(tmp_path):
    s = FileStorage(tmp_path/'db')
    run(s,'CREATE TABLE t(id INT); CREATE TABLE choices(id INT); INSERT INTO t VALUES(-1),(1),(2),(NULL); INSERT INTO choices VALUES(1); CREATE INDEX ix ON t(id);')
    return s


@pytest.mark.parametrize('where,expected', [('-1=id',[[-1]]), ('+1=id',[[1]]),
    ('id IN (SELECT id FROM choices)',[[1]]),
    ('id NOT IN (SELECT id FROM choices)',[[-1],[2]]),
    ('id=(SELECT id FROM choices)',[[1]]), ('(SELECT id FROM choices)=id',[[1]]),
    ('id IN (SELECT id AS x FROM choices ORDER BY x)',[[1]])])
def test_indexed_subqueries_and_reversed_signs(db,monkeypatch,where,expected):
    original = db.scan
    counts = []
    def scan(table):
        assert table != 't', 'indexed outer table scan'
        counts.append(table)
        return original(table)
    monkeypatch.setattr(db,'scan',scan)
    assert run(db,f'SELECT id FROM t WHERE {where} ORDER BY id;').rows == expected
    assert counts.count('choices') <= 1


def test_uncorrelated_query_is_evaluated_once_without_outer_index(db,monkeypatch):
    run(db,'DROP INDEX ix;')
    original = db.scan
    seen=[]
    def scan(table):
        seen.append(table)
        return original(table)
    monkeypatch.setattr(db,'scan',scan)
    assert run(db,'SELECT id FROM t WHERE id IN (SELECT id FROM choices);').rows == [[1]]
    assert seen.count('choices') == 1


def test_correlated_queries_keep_per_row_scope(db):
    assert run(db,'SELECT id FROM t x WHERE id IN (SELECT id FROM choices y WHERE y.id=x.id);').rows == [[1]]
    assert run(db,'SELECT id FROM t x WHERE EXISTS(SELECT * FROM choices y WHERE y.id=x.id);').rows == [[1]]


def test_dynamic_analysis_is_read_only_and_checks_even_empty_outer(db):
    run(db,'INSERT INTO choices VALUES(2); DELETE FROM t;')
    before = {p:p.read_bytes() for p in db.root.rglob('*') if p.is_file()}
    result = analyze_sql('SELECT * FROM t WHERE id=(SELECT id FROM choices);',db.catalog,storage=db)
    assert not result.accepted
    assert 'más de una fila' in result.diagnostics[0].message
    assert {p:p.read_bytes() for p in db.root.rglob('*') if p.is_file()} == before


def test_preflight_prevents_update_before_invalid_scalar(db,monkeypatch):
    run(db,'INSERT INTO choices VALUES(2);')
    before = (db.root/'manifest.json').read_bytes()
    import sql_interpreter.interpreter as module
    monkeypatch.setattr(module.Interpreter,'execute',lambda *a: pytest.fail('execution before preflight'))
    assert not execute_sql('UPDATE t SET id=7 WHERE id=(SELECT id FROM choices);',db).accepted
    assert (db.root/'manifest.json').read_bytes() == before


def test_not_in_null_empty_and_duplicate_sets(db):
    run(db,'INSERT INTO choices VALUES(1),(NULL);')
    assert run(db,'SELECT id FROM t WHERE id IN (SELECT id FROM choices);').rows == [[1]]
    assert run(db,'SELECT id FROM t WHERE id NOT IN (SELECT id FROM choices);').rows == []
    run(db,'DELETE FROM choices;')
    assert run(db,'SELECT id FROM t WHERE id NOT IN (SELECT id FROM choices) ORDER BY id;').rows == [[-1],[1],[2],[None]]
    assert run(db,'SELECT id FROM t WHERE id IN (SELECT id FROM choices);').rows == []


def test_correlated_scalar_is_checked_for_each_outer_row(db):
    run(db,'INSERT INTO choices VALUES(2),(2);')
    before = (db.root/'manifest.json').read_bytes()
    result = analyze_sql('SELECT id FROM t x WHERE id=(SELECT id FROM choices y WHERE y.id=x.id);',storage=db)
    assert not result.accepted
    assert (db.root/'manifest.json').read_bytes() == before


def test_cache_is_not_reused_after_mutating_statement(db):
    result = execute_sql('SELECT id FROM t WHERE id IN (SELECT id FROM choices); UPDATE choices SET id=2; SELECT id FROM t WHERE id IN (SELECT id FROM choices);',db)
    assert result.accepted,result.diagnostics
    assert result.results[0].rows == [[1]]
    assert result.results[2].rows == [[2]]

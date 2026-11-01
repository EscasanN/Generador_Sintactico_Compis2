import json
import pytest
from sql_interpreter.api import analyze_sql, execute_sql
from sql_interpreter.storage import FileStorage


def execute(db,sql):
    result = execute_sql(sql,db)
    assert result.accepted,result.diagnostics
    return result.results[-1]


@pytest.mark.parametrize('value',["'ab'",'NULL'])
def test_analysis_rejects_known_invalid_literal(value):
    result = analyze_sql(f'CREATE TABLE t(v VARCHAR(1) NOT NULL); INSERT INTO t VALUES({value});')
    assert not result.accepted


def test_join_where_uses_index_on_qualified_table(tmp_path):
    db = FileStorage(tmp_path/'db')
    execute(db,'CREATE TABLE t(id INT); INSERT INTO t VALUES(1),(2); CREATE INDEX ix ON t(id);')
    result = execute(db,'SELECT t.id FROM t INNER JOIN t b ON t.id=b.id WHERE t.id=1;')
    assert result.rows == [[1]]
    assert result.stats['index_lookups'] == 1
    assert result.stats['row_reads'] == 3


def test_index_union_and_inequality(tmp_path,monkeypatch):
    db = FileStorage(tmp_path/'db')
    execute(db,'CREATE TABLE t(id INT); INSERT INTO t VALUES(1),(2),(3),(NULL); CREATE INDEX ix ON t(id);')
    monkeypatch.setattr(db,'scan',lambda *args: (_ for _ in ()).throw(AssertionError('scan')))
    assert execute(db,'SELECT id FROM t WHERE id=1 OR id=2 ORDER BY id;').rows == [[1],[2]]
    assert execute(db,'SELECT id FROM t WHERE id<>1 ORDER BY id;').rows == [[2],[3]]


@pytest.mark.parametrize('sql',[
    'SELECT SUM(v) FROM t;', 'SELECT AVG(v) FROM t;', 'SELECT v*v FROM t;',
    'INSERT INTO t VALUES(' + '9'*400 + ');',
    'INSERT INTO t VALUES(' + '9'*4500 + ');',
])
def test_numeric_errors_return_diagnostics_without_partial_write(tmp_path,sql):
    db = FileStorage(tmp_path/'db')
    execute(db,'CREATE TABLE t(v FLOAT); INSERT INTO t VALUES(1e308),(1e308);')
    before = (db.root/'manifest.json').read_bytes()
    result = execute_sql(sql,db)
    assert not result.accepted
    assert result.diagnostics
    assert (db.root/'manifest.json').read_bytes() == before


def test_subquery_projection_is_explicitly_outside_dialect():
    result = analyze_sql('CREATE TABLE t(g INT,id INT); SELECT x.g,(SELECT MAX(y.id) FROM t y WHERE y.id=x.id) FROM t x GROUP BY x.g;')
    assert not result.accepted


def test_computed_integer_limit_is_diagnostic_before_storage_write(tmp_path):
    db = FileStorage(tmp_path/'db')
    execute(db,'CREATE TABLE t(n INT); INSERT INTO t VALUES('+ '9'*2200 +');')
    before = (db.root/'manifest.json').read_bytes()
    assert not execute_sql('UPDATE t SET n=n*n;',db).accepted
    assert (db.root/'manifest.json').read_bytes() == before
    assert not execute_sql('SELECT n*n FROM t;',db).accepted


def test_oversized_varchar_length_is_located():
    result = analyze_sql('CREATE TABLE t(n VARCHAR('+ '9'*4500 +'));')
    assert not result.accepted
    assert result.diagnostics[0].location.column > 1


def test_correlated_aggregate_uses_outer_column_as_constant(tmp_path):
    db = FileStorage(tmp_path/'db')
    execute(db,'CREATE TABLE t(id INT); INSERT INTO t VALUES(1),(2);')
    assert execute(db,'SELECT id FROM t x WHERE id=(SELECT COUNT(*)+x.id FROM t y WHERE y.id>99) ORDER BY id;').rows == [[1],[2]]


def test_indexed_dml_uses_candidates_and_updates_persisted_index(tmp_path):
    db = FileStorage(tmp_path/'db')
    execute(db,'CREATE TABLE t(id INT); INSERT INTO t VALUES(1),(2); CREATE INDEX ix ON t(id);')
    assert execute(db,'UPDATE t SET id=3 WHERE id=2;').stats['index_lookups'] == 1
    assert execute(db,'DELETE FROM t WHERE id=1;').stats['index_lookups'] == 1
    reopened = FileStorage(db.root)
    assert execute(reopened,'SELECT id FROM t WHERE id=3;').rows == [[3]]


def test_parse_failure_prevents_all_script_writes(tmp_path):
    db = FileStorage(tmp_path/'db')
    assert not execute_sql('CREATE TABLE t(id INT); INSERT INTO t VALUES(;',db).accepted
    assert not db.root.exists()


def test_script_semantic_failure_preserves_completed_statement(tmp_path):
    db = FileStorage(tmp_path/'db')
    assert not execute_sql('CREATE TABLE t(id INT); INSERT INTO t VALUES(TRUE);',db).accepted
    assert execute(db,'SELECT * FROM t;').rows == []


@pytest.mark.parametrize('typ,value', [('VARCHAR(4)',"'uno'"),('BOOLEAN','TRUE'),('DATE',"DATE '2026-10-30'"),('FLOAT','2.5')])
def test_indexed_types_persist_and_read_one_row(tmp_path,monkeypatch,typ,value):
    db = FileStorage(tmp_path/'db')
    execute(db,f'CREATE TABLE t(v {typ}); INSERT INTO t VALUES({value}),(NULL); CREATE INDEX ix ON t(v);')
    reopened = FileStorage(db.root)
    monkeypatch.setattr(reopened,'scan',lambda *args: (_ for _ in ()).throw(AssertionError('scan')))
    result = execute(reopened,f'SELECT * FROM t WHERE v={value};')
    assert len(result.rows) == 1
    assert result.stats['row_reads'] == 1

import importlib
import pytest


def api():
    return importlib.import_module('sql_interpreter.api')


def run(db, sql):
    result = api().execute_sql(sql, db)
    assert result.accepted, result.diagnostics
    return result.results[-1]


@pytest.fixture
def db(tmp_path):
    from sql_interpreter.storage import FileStorage
    return FileStorage(tmp_path / 'db')


def test_ddl_insert_reopen_and_projection(db):
    run(db, "CREATE TABLE t (id INT PRIMARY KEY, n VARCHAR(4), f FLOAT, b BOOLEAN, d DATE); INSERT INTO t VALUES (1,'Ana',2,TRUE,DATE '2024-02-29');")
    from sql_interpreter.storage import FileStorage
    reopened = FileStorage(db.root)
    assert run(reopened, 'SELECT n,f,b,d FROM t WHERE id=1;').rows == [['Ana',2.0,True,'2024-02-29']]
    run(reopened, 'DROP TABLE t;')
    assert not reopened.catalog['tables']


@pytest.mark.parametrize('sql', [
    "INSERT INTO t VALUES ('x','ok');", "INSERT INTO t VALUES (1,'12345');",
    "INSERT INTO t VALUES (1,'ok'),(1,'no');", "INSERT INTO t VALUES (NULL,'ok');",
    "UPDATE t SET id='x';", "SELECT missing FROM t;", "SELECT * FROM nowhere;",
    "SELECT id FROM t a INNER JOIN t b ON a.id=b.id;",
    "SELECT * FROM t WHERE id='x';", "SELECT * FROM t WHERE id+1;",
    "CREATE INDEX ix ON t(missing);", "DROP INDEX missing;",
])
def test_invalid_statements_do_not_change_files(db, sql):
    run(db, 'CREATE TABLE t (id INT PRIMARY KEY, n VARCHAR(4)); INSERT INTO t VALUES (9,\'ok\');')
    before = {p.relative_to(db.root): p.read_bytes() for p in db.root.rglob('*') if p.is_file()}
    result = api().execute_sql(sql, db)
    assert not result.accepted
    assert result.diagnostics[0].location.column >= 1
    assert {p.relative_to(db.root): p.read_bytes() for p in db.root.rglob('*') if p.is_file()} == before


def test_analyze_simulates_catalog_without_files(db):
    result = api().analyze_sql('CREATE TABLE t (id INT); INSERT INTO t VALUES (1); SELECT id FROM t;', db.catalog)
    assert result.accepted, result.diagnostics
    assert not db.root.exists()
    assert not db.catalog['tables']


def test_dml_order_and_null_logic(db):
    run(db, "CREATE TABLE t (id INT, n VARCHAR(5)); INSERT INTO t VALUES (1,NULL),(2,'dos'),(3,'tres');")
    assert run(db, 'SELECT id FROM t WHERE n=NULL OR id=2;').rows == [[2]]
    run(db, 'UPDATE t SET id=id+10 WHERE id>=2; DELETE FROM t WHERE n IS NULL;')
    assert run(db, 'SELECT id FROM t ORDER BY id DESC;').rows == [[13],[12]]


def test_join_group_and_aggregates(db):
    run(db, 'CREATE TABLE a (id INT); CREATE TABLE b (aid INT, v FLOAT); INSERT INTO a VALUES (1),(2); INSERT INTO b VALUES (1,2),(1,4),(2,NULL);')
    assert run(db, 'SELECT a.id,COUNT(*),COUNT(b.v),SUM(b.v),AVG(b.v),MIN(b.v),MAX(b.v) FROM a INNER JOIN b ON a.id=b.aid GROUP BY a.id HAVING COUNT(*)>1 ORDER BY a.id;').rows == [[1,2,2,6.0,3.0,2.0,4.0]]
    assert run(db, 'SELECT COUNT(*),SUM(v) FROM b WHERE aid=99;').rows == [[0,None]]
    assert not api().execute_sql('SELECT aid,v FROM b GROUP BY aid;', db).accepted


def test_subqueries_correlated_and_scalar_cardinality(db):
    run(db, 'CREATE TABLE a (id INT); CREATE TABLE b (id INT); INSERT INTO a VALUES (1),(2),(3); INSERT INTO b VALUES (2),(NULL);')
    assert run(db, 'SELECT id FROM a WHERE id IN (SELECT id FROM b);').rows == [[2]]
    assert run(db, 'SELECT id FROM a WHERE id NOT IN (SELECT id FROM b);').rows == []
    assert run(db, 'SELECT id FROM a WHERE EXISTS (SELECT * FROM b WHERE b.id=a.id);').rows == [[2]]
    assert run(db, 'SELECT id FROM a WHERE NOT EXISTS (SELECT * FROM b WHERE b.id=a.id) ORDER BY id;').rows == [[1],[3]]
    assert run(db, 'SELECT id FROM a WHERE id=(SELECT MAX(id) FROM b);').rows == [[2]]
    assert not api().execute_sql('SELECT * FROM a WHERE id=(SELECT id FROM b);', db).accepted
    assert not api().execute_sql('SELECT * FROM a WHERE id=(SELECT id,id FROM b);', db).accepted
    assert run(db, 'SELECT id FROM a WHERE id=(SELECT id FROM b WHERE id=99);').rows == []


def test_index_real_direct_reads_and_maintenance(db, monkeypatch):
    run(db, 'CREATE TABLE t (id INT, v VARCHAR(5)); INSERT INTO t VALUES (1,\'a\'),(2,\'b\'),(3,\'c\'); CREATE INDEX ix ON t(id);')
    from sql_interpreter.storage import FileStorage
    reopened = FileStorage(db.root)
    def no_scan(*args):
        raise AssertionError('hidden table scan')
    monkeypatch.setattr(reopened, 'scan', no_scan)
    result = run(reopened, 'SELECT v FROM t WHERE id=2;')
    assert result.rows == [['b']]
    assert result.stats['row_reads'] == 1 and result.stats['index_lookups'] == 1
    assert run(reopened, 'SELECT id FROM t WHERE id>=2 ORDER BY id;').rows == [[2],[3]]
    run(db, "UPDATE t SET id=5 WHERE id=2; DELETE FROM t WHERE id=1; INSERT INTO t VALUES (7,'d');")
    reopened = FileStorage(db.root)
    monkeypatch.setattr(reopened, 'scan', no_scan)
    assert run(reopened, 'SELECT id FROM t WHERE id>=3 ORDER BY id;').rows == [[3],[5],[7]]
    assert run(reopened, 'SELECT id FROM t WHERE id=2;').rows == []
    run(db, 'DROP INDEX ix;')
    assert not db.catalog['indexes']


@pytest.mark.parametrize('value', ["DATE '2023-02-29'", "DATE '2024-13-01'", "'2024-01-01'"])
def test_invalid_dates_and_no_implicit_text_cast(db, value):
    run(db, 'CREATE TABLE t (d DATE);')
    assert not api().execute_sql(f'INSERT INTO t VALUES ({value});', db).accepted


def test_index_conjunction_and_numeric_equivalence(db, monkeypatch):
    run(db, 'CREATE TABLE t(id INT, f FLOAT); INSERT INTO t VALUES(1,2),(2,3); CREATE INDEX ix ON t(id); CREATE INDEX fx ON t(f);')
    monkeypatch.setattr(db,'scan',lambda *a: (_ for _ in ()).throw(AssertionError('scan')))
    assert run(db, 'SELECT id FROM t WHERE id=1 AND f=2;').rows == [[1]]
    assert run(db, 'SELECT id FROM t WHERE id=1.0;').rows == [[1]]
    assert run(db, 'SELECT id FROM t WHERE f=2;').rows == [[1]]


def test_update_validation_is_atomic_for_all_rows(db):
    run(db,'CREATE TABLE t(id INT UNIQUE, v VARCHAR(2)); INSERT INTO t VALUES(1,\'a\'),(2,\'b\');')
    before = (db.root / 'manifest.json').read_bytes()
    assert not api().execute_sql('UPDATE t SET id=9;',db).accepted
    assert (db.root / 'manifest.json').read_bytes() == before
    assert run(db,'SELECT id FROM t ORDER BY id;').rows == [[1],[2]]


def test_group_qualified_column_and_order_alias(db):
    run(db,'CREATE TABLE t(id INT); INSERT INTO t VALUES(1),(1),(2);')
    assert run(db,'SELECT t.id AS x,COUNT(*) AS n FROM t GROUP BY id ORDER BY n DESC,x;').rows == [[1,2],[2,1]]


def test_negative_where_uses_index(db,monkeypatch):
    run(db,'CREATE TABLE t(id INT); INSERT INTO t VALUES(-1),(1); CREATE INDEX ix ON t(id);')
    monkeypatch.setattr(db,'scan',lambda *a: (_ for _ in ()).throw(AssertionError('scan')))
    assert run(db,'SELECT id FROM t WHERE id=-1;').rows == [[-1]]

"""Regresiones de la auditoría: errores controlados y trabajo proporcional al cambio."""
import json
import os
from pathlib import Path

import pytest

from sql_interpreter.api import analyze_sql, execute_sql
from sql_interpreter.storage import FileStorage


def run(db, sql):
    result = execute_sql(sql, db, source_path='audit.sql')
    assert result.accepted, result.diagnostics
    return result.results[-1]


def row_path(db, table, rid):
    manifest = json.loads((db.root / 'manifest.json').read_text(encoding='utf-8'))
    rows = json.loads((db.generation / 'rows.json').read_text(encoding='utf-8'))
    owner = rows[table][rid] if manifest['format'] == 2 else db.generation.name
    return db.root / 'generations' / owner / 'tables' / table / f'{rid}.json'


@pytest.mark.parametrize('damage', ['{broken', '[]', '{"other":1}', '{"id":"wrong type"}'])
def test_corrupt_row_returns_located_storage_diagnostic(tmp_path, damage):
    db = FileStorage(tmp_path / 'db')
    run(db, 'CREATE TABLE t(id INT); INSERT INTO t VALUES(1);')
    path = row_path(db, 't', db.row_ids['t'][0])
    path.write_text(damage, encoding='utf-8')
    before = (db.root / 'manifest.json').read_bytes()
    result = execute_sql('\nSELECT * FROM t;', db, source_path='bad.sql')
    assert not result.accepted
    error = result.diagnostics[0]
    assert error.stage == 'STORAGE'
    assert str(path) in error.message
    assert error.location.line == 2 and error.location.source_path == 'bad.sql'
    assert (db.root / 'manifest.json').read_bytes() == before


def test_corrupt_index_is_diagnostic_and_not_silent_scan(tmp_path):
    db = FileStorage(tmp_path / 'db')
    run(db, 'CREATE TABLE t(id INT); INSERT INTO t VALUES(1); CREATE INDEX ix ON t(id);')
    (db.generation / 'indexes/ix.json').write_text('{broken', encoding='utf-8')
    result = execute_sql('SELECT * FROM t WHERE id=1;', db)
    assert not result.accepted
    assert result.diagnostics[0].stage == 'STORAGE'
    assert 'ix.json' in result.diagnostics[0].message


@pytest.mark.parametrize('query,expected', [
    ('EXISTS(SELECT 1/0 FROM t)', [[1],[2]]),
    ('NOT EXISTS(SELECT 1/0 FROM t)', []),
    ('EXISTS(SELECT 1/0 FROM t y WHERE y.id=x.id)', [[1],[2]]),
    ('EXISTS(SELECT 1/0 FROM t ORDER BY 1/0)', [[1],[2]]),
    ('EXISTS(SELECT COUNT(*)/0 FROM t WHERE id>99)', [[1],[2]]),
    ('EXISTS(SELECT 1/0 FROM t GROUP BY id HAVING COUNT(*)>1)', []),
    ('NOT EXISTS(SELECT 1/0 FROM t WHERE id>99)', [[1],[2]]),
])
def test_exists_uses_cardinality_not_projection(tmp_path, query, expected):
    db = FileStorage(tmp_path / 'db')
    run(db, 'CREATE TABLE t(id INT); INSERT INTO t VALUES(1),(2);')
    assert run(db, f'SELECT id FROM t x WHERE {query} ORDER BY id;').rows == expected


def test_exists_still_evaluates_where_and_having(tmp_path):
    db = FileStorage(tmp_path / 'db')
    run(db, 'CREATE TABLE t(id INT); INSERT INTO t VALUES(1);')
    for predicate in ['WHERE 1/0=1', 'HAVING 1/0=COUNT(*)']:
        result = execute_sql(f'SELECT id FROM t WHERE EXISTS(SELECT COUNT(*) FROM t {predicate});', db)
        assert not result.accepted


def test_subquery_in_on_is_rejected_consistently():
    result = analyze_sql('CREATE TABLE t(id INT); SELECT * FROM t a INNER JOIN t b ON EXISTS(SELECT * FROM t);')
    assert not result.accepted
    assert result.diagnostics[0].stage == 'SEMANTIC'


@pytest.fixture
def window(tmp_path):
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from PyQt6.QtWidgets import QApplication
    from sql_interpreter.gui import MainWindow
    app = QApplication.instance() or QApplication([])
    view = MainWindow(tmp_path / 'db')
    yield view
    view.editor.document().setModified(False)
    view.close()


def test_failed_partial_document_write_preserves_original(window, tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox
    import sql_interpreter.gui as gui
    path = tmp_path / 'original.sql'
    path.write_text('SELECT original;', encoding='utf-8')
    window.path = str(path)
    window.editor.setPlainText('SELECT reemplazo;')
    window.editor.document().setModified(True)
    original_write = Path.write_text

    def partial_write(target, text, *args, **kwargs):
        original_write(target, text[:4], *args, **kwargs)
        raise OSError('disco lleno')

    monkeypatch.setattr(Path, 'write_text', partial_write)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: None)
    assert not window.save_document()
    assert path.read_text(encoding='utf-8') == 'SELECT original;'
    assert window.editor.toPlainText() == 'SELECT reemplazo;'
    assert window.editor.document().isModified()
    assert sorted(p.name for p in tmp_path.iterdir()) == ['original.sql']


def test_failed_document_replace_preserves_file_and_path(window, tmp_path, monkeypatch):
    import sql_interpreter.gui as gui
    from PyQt6.QtWidgets import QFileDialog, QMessageBox
    original = tmp_path / 'original.sql'
    original.write_text('original', encoding='utf-8')
    destination = tmp_path / 'existing.sql'
    destination.write_text('destino', encoding='utf-8')
    window.path = str(original)
    window.editor.setPlainText('nuevo')
    window.editor.document().setModified(True)
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a: (str(destination), ''))
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: None)
    def fail_replace(*args):
        raise OSError('archivo bloqueado')
    monkeypatch.setattr(os, 'replace', fail_replace)
    assert not window.save_as()
    assert window.path == str(original)
    assert destination.read_text(encoding='utf-8') == 'destino'
    assert window.editor.document().isModified()
    assert sorted(p.name for p in tmp_path.iterdir()) == ['existing.sql', 'original.sql']


def test_successful_document_save_replaces_complete_text(window, tmp_path):
    path = tmp_path / 'consulta.sql'
    path.write_text('viejo', encoding='utf-8')
    window.path = str(path)
    window.editor.setPlainText("SELECT 'María';")
    assert window.save_document()
    assert path.read_text(encoding='utf-8') == "SELECT 'María';"
    assert not window.editor.document().isModified()


def test_indexed_update_only_reads_and_writes_changed_row(tmp_path, monkeypatch):
    db = FileStorage(tmp_path / 'db')
    run(db, 'CREATE TABLE t(id INT); CREATE TABLE untouched(id INT); INSERT INTO t VALUES(1),(2); INSERT INTO untouched VALUES(99); CREATE INDEX ix ON t(id);')
    old = {rid:row_path(db,'t',rid) for rid in db.row_ids['t']}
    old_other = row_path(db,'untouched',db.row_ids['untouched'][0])
    old_bytes = {path:path.read_bytes() for path in list(old.values()) + [old_other]}
    monkeypatch.setattr(db, 'scan', lambda *a: (_ for _ in ()).throw(AssertionError('whole-table scan')))
    result = run(db, 'UPDATE t SET id=3 WHERE id=2;')
    assert result.stats['row_reads'] == 1
    assert result.stats['row_writes'] == 1
    assert len(list(db.generation.glob('tables/*/*.json'))) == 1
    assert all(path.read_bytes() == content for path,content in old_bytes.items())
    assert row_path(db,'untouched',db.row_ids['untouched'][0]) == old_other
    reopened = FileStorage(db.root)
    assert run(reopened, 'SELECT id FROM t WHERE id=3;').rows == [[3]]
    assert run(reopened, 'SELECT id FROM untouched;').rows == [[99]]


def test_ddl_and_insert_do_not_read_unrelated_tables(tmp_path, monkeypatch):
    db = FileStorage(tmp_path / 'db')
    run(db, 'CREATE TABLE t(id INT); CREATE TABLE other(id INT); INSERT INTO other VALUES(99);')
    original_scan = db.scan
    def scan(table):
        assert table != 'other', 'read unrelated table'
        return original_scan(table)
    monkeypatch.setattr(db,'scan',scan)
    run(db,'INSERT INTO t VALUES(1); CREATE INDEX ix ON t(id); DROP INDEX ix; DROP TABLE t;')
    monkeypatch.undo()
    assert run(db,'SELECT * FROM other;').rows == [[99]]


def test_legacy_storage_migrates_on_write_and_keeps_snapshot(tmp_path):
    root = tmp_path / 'legacy'
    generation = root / 'generations/v1'
    generation.mkdir(parents=True)
    catalog = {'tables': {'t': {'columns': [{'name':'id','type':'INT','size':None,'constraints':[]}]}},
               'indexes': {'ix': {'table':'t','column':'id'}}}
    files = {'manifest.json': {'generation':'v1','format':1},
             'generations/v1/catalog.json': catalog,
             'generations/v1/rows.json': {'t':['one','two']},
             'generations/v1/tables/t/one.json': {'id':1},
             'generations/v1/tables/t/two.json': {'id':2},
             'generations/v1/indexes/ix.json': {'["number",1]':['one'],'["number",2]':['two']}}
    for name,value in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')
    old_files = {p:p.read_bytes() for p in generation.rglob('*') if p.is_file()}
    old_view = FileStorage(root)
    writer = FileStorage(root)
    assert run(writer,'SELECT id FROM t WHERE id=2;').rows == [[2]]
    run(writer,'UPDATE t SET id=3 WHERE id=2;')
    assert json.loads((root/'manifest.json').read_text())['format'] == 2
    reopened = FileStorage(root)
    assert run(reopened,'SELECT id FROM t ORDER BY id;').rows == [[1],[3]]
    assert run(reopened,'SELECT id FROM t WHERE id=3;').rows == [[3]]
    assert old_view.scan('t') == [('one',{'id':1}),('two',{'id':2})]
    assert all(p.read_bytes() == content for p,content in old_files.items())


def test_failed_incremental_publish_keeps_data_and_index(tmp_path,monkeypatch):
    db = FileStorage(tmp_path/'db')
    run(db,'CREATE TABLE t(id INT); INSERT INTO t VALUES(1),(2); CREATE INDEX ix ON t(id);')
    before = (db.root/'manifest.json').read_bytes()
    def fail(*args):
        raise OSError('publish failure')
    monkeypatch.setattr(db,'_publish',fail)
    result = execute_sql('UPDATE t SET id=3 WHERE id=2;',db)
    assert not result.accepted
    assert result.diagnostics[0].stage == 'STORAGE'
    assert (db.root/'manifest.json').read_bytes() == before
    reopened = FileStorage(db.root)
    assert run(reopened,'SELECT id FROM t WHERE id=2;').rows == [[2]]
    assert run(reopened,'SELECT id FROM t WHERE id=3;').rows == []


def test_incremental_delete_insert_keep_other_row_files_and_indexes(tmp_path,monkeypatch):
    db = FileStorage(tmp_path/'db')
    run(db,'CREATE TABLE t(id INT); INSERT INTO t VALUES(1),(2); CREATE INDEX ix ON t(id);')
    survivor = run(db,'SELECT id FROM t WHERE id=1;').rows
    monkeypatch.setattr(db,'scan',lambda *a: (_ for _ in ()).throw(AssertionError('scan')))
    assert run(db,'DELETE FROM t WHERE id=2;').stats['row_writes'] == 0
    assert run(db,'INSERT INTO t VALUES(3);').stats['row_writes'] == 1
    assert run(db,'SELECT id FROM t WHERE id=1;').rows == survivor
    reopened = FileStorage(db.root)
    assert run(reopened,'SELECT id FROM t WHERE id>=0 ORDER BY id;').rows == [[1],[3]]


def test_incremental_unique_validation_is_atomic_and_table_local(tmp_path,monkeypatch):
    db = FileStorage(tmp_path/'db')
    run(db,'CREATE TABLE t(id INT UNIQUE); CREATE TABLE other(id INT); INSERT INTO t VALUES(1),(2); INSERT INTO other VALUES(7);')
    before = (db.root/'manifest.json').read_bytes()
    original = db.scan
    def scan(table):
        assert table == 't', 'unrelated constraint scan'
        return original(table)
    monkeypatch.setattr(db,'scan',scan)
    assert not execute_sql('UPDATE t SET id=9;',db).accepted
    assert (db.root/'manifest.json').read_bytes() == before
    # Un swap simultáneo válido no debe fallar por evaluar estados intermedios.
    run(db,'UPDATE t SET id=3-id;')
    assert run(db,'SELECT id FROM t ORDER BY id;').rows == [[1],[2]]


def test_missing_row_file_is_located_diagnostic(tmp_path):
    db = FileStorage(tmp_path/'db')
    run(db,'CREATE TABLE t(id INT); INSERT INTO t VALUES(1);')
    row_path(db,'t',db.row_ids['t'][0]).unlink()
    result = execute_sql('SELECT * FROM t;',db)
    assert not result.accepted
    assert result.diagnostics[0].stage == 'STORAGE'


@pytest.mark.parametrize('field', ['table','column'])
def test_corrupt_index_definition_never_leaks_type_error(tmp_path,field):
    db = FileStorage(tmp_path/'db')
    run(db,'CREATE TABLE t(id INT); CREATE INDEX ix ON t(id);')
    path = db.generation/'catalog.json'
    catalog = json.loads(path.read_text(encoding='utf-8'))
    catalog['indexes']['ix'][field] = []
    path.write_text(json.dumps(catalog),encoding='utf-8')
    result = execute_sql('SELECT * FROM t;',db)
    assert not result.accepted
    assert result.diagnostics[0].stage == 'STORAGE'
    assert 'catalog.json' in result.diagnostics[0].message


@pytest.mark.parametrize('damage', ['duplicate','across_keys','missing','empty','wrong_type'])
def test_index_rids_are_unique_and_cover_table_metadata(tmp_path,damage):
    db = FileStorage(tmp_path/'db')
    run(db,'CREATE TABLE t(id INT); INSERT INTO t VALUES(1),(2); CREATE INDEX ix ON t(id);')
    path = db.generation/'indexes/ix.json'
    entries = json.loads(path.read_text(encoding='utf-8'))
    first,second = '["number",1]', '["number",2]'
    if damage == 'duplicate':
        entries[first] *= 2
    elif damage == 'across_keys':
        entries[second] = entries[first]
    elif damage == 'missing':
        del entries[second]
    elif damage == 'empty':
        entries = {}
    else:
        entries['["str","one"]'] = entries.pop(first)
    path.write_text(json.dumps(entries),encoding='utf-8')
    result = execute_sql('SELECT id FROM t WHERE id=1;',db)
    assert not result.accepted
    assert result.diagnostics[0].stage == 'STORAGE'
    assert 'ix.json' in result.diagnostics[0].message


def test_invalid_stored_date_is_a_storage_error(tmp_path):
    db = FileStorage(tmp_path/'db')
    run(db,"CREATE TABLE t(d DATE); INSERT INTO t VALUES(DATE '2024-02-29');")
    row_path(db,'t',db.row_ids['t'][0]).write_text('{"d":"2024-02-30"}',encoding='utf-8')
    result = execute_sql('SELECT * FROM t;',db)
    assert not result.accepted
    assert result.diagnostics[0].stage == 'STORAGE'

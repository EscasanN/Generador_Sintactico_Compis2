"""Integridad referencial persistente y protección del esquema ante DROP."""
import json

import pytest

from sql_interpreter.api import analyze_sql, execute_sql
from sql_interpreter.ast import build_ast
from sql_interpreter.frontend import parse_sql
from sql_interpreter.storage import FileStorage


def run(db, sql):
    result = execute_sql(sql, db, source_path='foreign_keys.sql')
    assert result.accepted, result.diagnostics
    return result


def snapshot(db):
    return {p.relative_to(db.root): p.read_bytes() for p in db.root.rglob('*') if p.is_file()}


@pytest.fixture
def db(tmp_path):
    return FileStorage(tmp_path/'db')


def parents(db):
    run(db,'CREATE TABLE estudiantes(id INT PRIMARY KEY); INSERT INTO estudiantes VALUES(1),(2);')


def child(db):
    run(db,'''CREATE TABLE inscripciones (
        id INT PRIMARY KEY,
        estudiante_id INT REFERENCES estudiantes(id)
    );''')


def test_ast_supports_both_declaration_forms_and_alter():
    sql = '''CREATE TABLE t(id INT PRIMARY KEY);
    CREATE TABLE a(id INT REFERENCES t(id));
    CREATE TABLE b(id INT, FOREIGN KEY(id) REFERENCES t(id));
    ALTER TABLE b ADD FOREIGN KEY(id) REFERENCES t(id);'''
    result = parse_sql(sql)
    assert result.accepted, result.diagnostics
    ast = build_ast(result)
    for command in ast.statements[1:]:
        fk = command.foreign_keys[0]
        assert (fk.column, fk.referenced_table, fk.referenced_column) == ('id','t','id')
        assert fk.location.line >= 1
    assert ast.statements[-1].kind == 'add_foreign_key'


@pytest.mark.parametrize('populated',[False,True])
def test_drop_parent_is_rejected_and_files_unchanged_after_reopen(db,populated):
    parents(db)
    child(db)
    if populated:
        run(db,'INSERT INTO inscripciones VALUES(1,1);')
    before = snapshot(db)
    reopened = FileStorage(db.root)
    result = execute_sql('\nDROP TABLE estudiantes;',reopened)
    assert not result.accepted
    error = result.diagnostics[0]
    assert error.stage == 'SEMANTIC' and error.location.line == 2
    assert 'inscripciones' in error.message and 'estudiantes' in error.message
    assert snapshot(db) == before
    assert not analyze_sql('DROP TABLE estudiantes;',storage=reopened).accepted
    assert run(reopened,'SELECT id FROM estudiantes ORDER BY id;').results[-1].rows == [[1],[2]]


def test_drop_child_then_parent_is_allowed(db):
    parents(db)
    child(db)
    run(db,'DROP TABLE inscripciones; DROP TABLE estudiantes;')
    assert db.catalog['tables'] == {}


def test_similar_column_names_do_not_create_implicit_dependencies(db):
    parents(db)
    run(db,'CREATE TABLE inscripciones(estudiante_id INT); DROP TABLE estudiantes;')
    assert 'inscripciones' in db.catalog['tables']


def test_alter_adds_dependency_to_existing_data_without_rewriting_rows(db):
    parents(db)
    run(db,'CREATE TABLE inscripciones(estudiante_id INT); INSERT INTO inscripciones VALUES(1),(NULL);')
    old_rows = dict(db.row_generations['inscripciones'])
    run(db,'ALTER TABLE inscripciones ADD FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id);')
    assert db.row_generations['inscripciones'] == old_rows
    assert not execute_sql('DROP TABLE estudiantes;',FileStorage(db.root)).accepted
    assert run(db,'SELECT estudiante_id FROM inscripciones ORDER BY estudiante_id;').results[-1].rows == [[1],[None]]


def test_alter_rejects_orphans_atomically(db):
    parents(db)
    run(db,'CREATE TABLE inscripciones(estudiante_id INT); INSERT INTO inscripciones VALUES(99);')
    before = snapshot(db)
    result = execute_sql('ALTER TABLE inscripciones ADD FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id);',db)
    assert not result.accepted
    assert snapshot(db) == before
    assert not db.catalog['tables']['inscripciones'].get('foreign_keys')


@pytest.mark.parametrize('sql',[
    'INSERT INTO inscripciones VALUES(1,1),(2,99);',
    'UPDATE inscripciones SET estudiante_id=99;',
    'DELETE FROM estudiantes WHERE id=1;',
    'UPDATE estudiantes SET id=3 WHERE id=1;',
])
def test_dml_cannot_break_reference_and_keeps_all_files(db,sql):
    parents(db)
    child(db)
    run(db,'INSERT INTO inscripciones VALUES(8,1); CREATE INDEX ix ON estudiantes(id);')
    before = snapshot(db)
    result = execute_sql(sql,db)
    assert not result.accepted
    assert 'refer' in result.diagnostics[0].message.lower()
    assert snapshot(db) == before


def test_null_and_unreferenced_parent_changes_are_allowed(db):
    parents(db)
    child(db)
    run(db,'INSERT INTO inscripciones VALUES(1,NULL),(2,1); DELETE FROM estudiantes WHERE id=2;')
    run(db,'DELETE FROM inscripciones WHERE id=2; DELETE FROM estudiantes WHERE id=1;')
    assert run(db,'SELECT * FROM estudiantes;').results[-1].rows == []


@pytest.mark.parametrize('definition',[
    'CREATE TABLE c(id INT REFERENCES missing(id));',
    'CREATE TABLE c(id INT REFERENCES estudiantes(missing));',
    'CREATE TABLE c(id FLOAT REFERENCES estudiantes(id));',
    'CREATE TABLE c(id INT, FOREIGN KEY(missing) REFERENCES estudiantes(id));',
    'CREATE TABLE c(id INT REFERENCES estudiantes(id) REFERENCES estudiantes(id));',
    'ALTER TABLE estudiantes ADD FOREIGN KEY(missing) REFERENCES estudiantes(id);',
])
def test_invalid_definitions_do_not_publish(db,definition):
    parents(db)
    before = snapshot(db)
    result = execute_sql(definition,db)
    assert not result.accepted
    assert result.diagnostics[0].stage == 'SEMANTIC'
    assert snapshot(db) == before


def test_reference_requires_unique_parent_key(db):
    run(db,'CREATE TABLE p(id INT);')
    result = execute_sql('CREATE TABLE c(id INT REFERENCES p(id));',db)
    assert not result.accepted
    assert 'UNIQUE' in result.diagnostics[0].message or 'PRIMARY KEY' in result.diagnostics[0].message


def test_unique_parent_and_self_reference_final_state(db):
    run(db,'CREATE TABLE p(code VARCHAR(4) UNIQUE); INSERT INTO p VALUES(\'AA\');')
    run(db,"CREATE TABLE c(code VARCHAR(4) REFERENCES p(code)); INSERT INTO c VALUES('AA');")
    run(db,'''CREATE TABLE nodos(id INT PRIMARY KEY, padre INT REFERENCES nodos(id));
        INSERT INTO nodos VALUES(1,1),(2,1);''')
    assert not execute_sql('DELETE FROM nodos WHERE id=1;',db).accepted
    run(db,'DELETE FROM nodos; DROP TABLE nodos;')


def test_self_referencing_table_can_be_dropped(db):
    run(db,'CREATE TABLE nodos(id INT PRIMARY KEY,padre INT REFERENCES nodos(id)); DROP TABLE nodos;')
    assert db.catalog['tables'] == {}


def test_analyze_builds_dependencies_without_files(db):
    result = analyze_sql('''CREATE TABLE p(id INT PRIMARY KEY);
        CREATE TABLE c(pid INT REFERENCES p(id)); DROP TABLE p;''')
    assert not result.accepted
    assert result.diagnostics[0].stage == 'SEMANTIC'
    assert 'c' in result.diagnostics[0].message
    assert not db.root.exists()


def test_adding_same_reference_twice_is_rejected(db):
    parents(db)
    child(db)
    before = snapshot(db)
    assert not execute_sql('ALTER TABLE inscripciones ADD FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id);',db).accepted
    assert snapshot(db) == before


def test_self_reference_key_and_foreign_key_swap_is_simultaneous(db):
    run(db,'''CREATE TABLE nodes(id INT PRIMARY KEY,parent INT REFERENCES nodes(id));
        INSERT INTO nodes VALUES(1,2),(2,1);
        UPDATE nodes SET id=3-id,parent=3-parent;''')
    assert run(db,'SELECT id,parent FROM nodes ORDER BY id;').results[-1].rows == [[1,2],[2,1]]


def test_cycle_blocks_drop_but_null_can_break_data_dependency(db):
    run(db,'''CREATE TABLE a(id INT PRIMARY KEY,bid INT);
        CREATE TABLE b(id INT PRIMARY KEY,aid INT REFERENCES a(id));
        INSERT INTO a VALUES(1,NULL); INSERT INTO b VALUES(1,1);
        ALTER TABLE a ADD FOREIGN KEY(bid) REFERENCES b(id);
        UPDATE a SET bid=1;''')
    before = snapshot(db)
    assert not execute_sql('DROP TABLE a;',db).accepted
    assert not execute_sql('DROP TABLE b;',db).accepted
    assert not execute_sql('DELETE FROM b;',db).accepted
    assert snapshot(db) == before
    run(db,'UPDATE a SET bid=NULL; DELETE FROM b; DELETE FROM a;')


@pytest.mark.parametrize('damage',[
    None, 'bad', [None],
    [{'column':[],'referenced_table':'estudiantes','referenced_column':'id'}],
    [{'column':'estudiante_id','referenced_table':'missing','referenced_column':'id'}],
])
def test_corrupt_persisted_references_return_storage_diagnostic(db,damage):
    parents(db)
    child(db)
    path = db.generation/'catalog.json'
    catalog = json.loads(path.read_text(encoding='utf-8'))
    catalog['tables']['inscripciones']['foreign_keys'] = damage
    path.write_text(json.dumps(catalog),encoding='utf-8')
    result = execute_sql('SELECT * FROM estudiantes;',db)
    assert not result.accepted
    assert result.diagnostics[0].stage == 'STORAGE'


def test_gui_shows_dependency_error_without_dropping_table(db):
    import os
    import time
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from PyQt6.QtWidgets import QApplication
    from sql_interpreter.gui import MainWindow
    parents(db)
    child(db)
    before = snapshot(db)
    app = QApplication.instance() or QApplication([])
    window = MainWindow(db.root)
    window.editor.setPlainText('DROP TABLE estudiantes;')
    for action in (window.start_analysis,window.start_execution):
        action()
        deadline = time.monotonic()+15
        while window.worker is not None and time.monotonic() < deadline:
            app.processEvents()
        assert window.worker is None
        assert window.errors.rowCount() == 1
        assert 'inscripciones' in window.errors.item(0,3).text()
        assert snapshot(db) == before
    window.editor.document().setModified(False)
    window.close()


def test_transient_windows_manifest_lock_can_finish_publication(db,monkeypatch):
    import os
    parents(db)
    child(db)
    original = os.replace
    blocked = True
    def temporary_lock(source,target):
        nonlocal blocked
        if blocked:
            blocked = False
            error = PermissionError('manifest temporalmente bloqueado')
            error.winerror = 32
            raise error
        return original(source,target)
    monkeypatch.setattr(os,'replace',temporary_lock)
    run(db,'INSERT INTO inscripciones VALUES(1,1);')
    assert run(FileStorage(db.root),'SELECT * FROM inscripciones;').results[-1].rows == [[1,1]]


def test_persistent_windows_manifest_lock_returns_error_and_preserves_old_state(db,monkeypatch):
    import os
    parents(db)
    child(db)
    before = (db.root/'manifest.json').read_bytes()
    def lock(*args):
        error = PermissionError('manifest bloqueado')
        error.winerror = 32
        raise error
    monkeypatch.setattr(os,'replace',lock)
    result = execute_sql('INSERT INTO inscripciones VALUES(1,1);',db)
    assert not result.accepted
    assert result.diagnostics[0].stage == 'STORAGE'
    assert (db.root/'manifest.json').read_bytes() == before
    assert run(FileStorage(db.root),'SELECT * FROM inscripciones;').results[-1].rows == []

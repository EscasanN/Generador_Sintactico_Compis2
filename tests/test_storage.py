import importlib
import pytest


def storage(path):
    return importlib.import_module('sql_interpreter.storage').FileStorage(path)


def test_generation_commit_persists_and_fetches_rows_directly(tmp_path):
    store = storage(tmp_path / 'db')
    catalog = {'tables': {'t': {'columns': [{'name':'id','type':'INT','size':None,'constraints':[]}]}}, 'indexes': {}}
    store.commit(catalog, {'t': {'1': {'id':1}, '7': {'id':7}}})
    reopened = storage(tmp_path / 'db')
    assert reopened.catalog == catalog
    assert reopened.fetch('t', ['7']) == [('7', {'id':7})]
    assert reopened.stats['row_reads'] == 1
    assert reopened.stats['table_scans'] == 0


def test_failed_publish_keeps_previous_generation(tmp_path, monkeypatch):
    store = storage(tmp_path / 'db')
    store.commit({'tables':{},'indexes':{}}, {})
    before = (tmp_path / 'db/manifest.json').read_bytes()
    def fail(*args):
        raise OSError('disk failure')
    monkeypatch.setattr(store, '_publish', fail)
    with pytest.raises(OSError):
        store.commit({'tables':{'bad':{}} ,'indexes':{}}, {})
    assert (tmp_path / 'db/manifest.json').read_bytes() == before
    assert storage(tmp_path / 'db').catalog == {'tables':{},'indexes':{}}


def test_opening_missing_storage_is_read_only(tmp_path):
    store = storage(tmp_path / 'absent')
    assert store.catalog == {'tables':{},'indexes':{}}
    assert not (tmp_path / 'absent').exists()

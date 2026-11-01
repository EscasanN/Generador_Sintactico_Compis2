import builtins
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys


def test_analysis_does_not_open_files_for_write(monkeypatch):
    from sql_interpreter.api import analyze_sql
    from sql_interpreter.generated.SQLParser import SQLParser
    real_open = builtins.open
    def guarded(file, mode='r', *args, **kwargs):
        assert not any(c in mode for c in 'wax+'), 'analysis attempted write'
        return real_open(file,mode,*args,**kwargs)
    monkeypatch.setattr(builtins,'open',guarded)
    assert analyze_sql('CREATE TABLE t(id INT); SELECT * FROM t;').accepted


def test_cli_analyze_execute_and_reopen(tmp_path, capsys):
    main = importlib.import_module('sql_interpreter.cli').main
    sql = tmp_path / 'test.sql'
    sql.write_text('CREATE TABLE t(id INT); INSERT INTO t VALUES(7); SELECT * FROM t;',encoding='utf-8')
    root = tmp_path / 'db'
    assert main(['analyze',str(sql),'--database',str(root),'--json']) == 0
    assert json.loads(capsys.readouterr().out)['accepted']
    assert not root.exists()
    assert main(['execute',str(sql),'--database',str(root),'--json']) == 0
    assert json.loads(capsys.readouterr().out)['results'][-1]['rows'] == [[7]]
    sql.write_text('SELECT missing FROM t;',encoding='utf-8')
    assert main(['execute',str(sql),'--database',str(root),'--json']) == 1
    assert json.loads(capsys.readouterr().out)['diagnostics']


def test_gui_explicit_execution_and_panels(tmp_path):
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from PyQt6.QtWidgets import QApplication
    from sql_interpreter.gui import MainWindow
    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / 'db')
    window.editor.setPlainText('CREATE TABLE t(id INT); INSERT INTO t VALUES(3); SELECT * FROM t;')
    window.start_analysis()
    while window.worker is not None:
        app.processEvents()
    assert not (tmp_path / 'db').exists()
    assert window.tokens.rowCount() > 0
    assert window.tree.topLevelItemCount() > 0
    assert window.ast_tree.topLevelItemCount() > 0
    window.start_execution()
    while window.worker is not None:
        app.processEvents()
    assert window.results.rowCount() == 1
    assert window.results.item(0,0).text() == '3'
    assert (tmp_path / 'db/manifest.json').exists()
    window.editor.document().setModified(False)
    window.close()


def test_gui_cancel_document_replacement_keeps_buffer(tmp_path, monkeypatch):
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from sql_interpreter.gui import MainWindow
    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / 'db')
    window.editor.setPlainText('SELECT * FROM original;')
    window.editor.document().setModified(True)
    monkeypatch.setattr(QMessageBox,'question',lambda *a: QMessageBox.StandardButton.Cancel)
    window.new_document()
    assert window.editor.toPlainText() == 'SELECT * FROM original;'
    window.editor.document().setModified(False)
    window.close()

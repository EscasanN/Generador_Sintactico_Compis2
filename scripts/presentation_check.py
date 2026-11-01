"""Demostración reproducible usando exclusivamente el paquete instalado en un venv.

py scripts/presentation_check.py --python tmp/venv/Scripts/python.exe
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', required=True, type=Path)
    args = parser.parse_args()
    python = args.python.resolve()
    stage = Path(tempfile.mkdtemp(prefix='presentation-run-', dir=ROOT/'tmp'))
    db = stage/'database'
    examples = stage/'sql'
    shutil.copytree(ROOT/'examples/presentation', examples)
    env = os.environ | {'PYTHONIOENCODING':'utf-8', 'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONNOUSERSITE':'1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
    env.pop('PYTHONPATH', None)
    cases = []

    def process(command):
        if command[0] == str(python):
            command = [command[0], '-X', 'utf8'] + command[1:]
        p = subprocess.run(command, cwd=stage, env=env, capture_output=True, text=True, encoding='utf-8', timeout=180)
        return p

    def snapshot():
        return {str(p.relative_to(db)):hashlib.sha256(p.read_bytes()).hexdigest() for p in db.rglob('*') if p.is_file()}

    def cli(name, action, sql=None, file=None, accepted=True):
        file = examples/file if file else examples/f'{name}.sql'
        if sql is not None:
            file.write_text(sql, encoding='utf-8')
        p = process([str(python),'-I','-B','-m','sql_interpreter',action,str(file),'--database',str(db),'--json'])
        (stage/f'{name}.stdout.json').write_text(p.stdout,encoding='utf-8')
        (stage/f'{name}.stderr.txt').write_text(p.stderr,encoding='utf-8')
        result = json.loads(p.stdout)
        assert result['accepted'] == accepted, (name,p.stdout,p.stderr)
        assert p.returncode == (0 if accepted else 1), (name,p.returncode)
        return result

    def record(name, details):
        cases.append({'case':name,'status':'PASS','details':details})

    p = process([str(python),'-I','-c',
        'import json,sys,sql_interpreter,antlr4,PyQt6; from importlib.metadata import version; print(json.dumps({"python":sys.version,"prefix":sys.prefix,"base_prefix":sys.base_prefix,"package":sql_interpreter.__file__,"antlr":version("antlr4-python3-runtime"),"qt":version("PyQt6")}))'])
    assert p.returncode == 0,p.stderr
    environment = json.loads(p.stdout)
    assert environment['prefix'] != environment['base_prefix']
    assert Path(environment['package']).is_relative_to(Path(environment['prefix']))
    record('Entorno aislado',environment)
    p = process([str(python),'-I','-m','pip','check'])
    assert p.returncode == 0,p.stdout+p.stderr
    record('Dependencias',p.stdout.strip())

    result = cli('analyze_empty','analyze',file='01_setup.sql')
    assert not db.exists()
    assert result['tokens'] and result['tree'] and result['ast']
    record('Analizar sobre base inexistente','Aceptado; tokens/árbol/AST presentes; ningún archivo de base creado')
    cli('setup','execute',file='01_setup.sql')
    result = cli('types','execute','SELECT id,nombre,edad,promedio,activo,nacimiento FROM estudiantes ORDER BY id;')
    assert result['results'][-1]['rows'] == [[1,'Ana',20,90.0,True,'2004-02-29'],[2,'Luis',17,75.0,True,'2009-05-12'],[3,'María',22,None,False,'2004-08-03'],[4,'Pedro',19,60.0,True,'2007-01-01']]
    record('Tipos y esquema persistente',result['results'][-1]['rows'])
    result = cli('queries','execute',file='02_queries.sql')
    expected = [
        [['María',22],['Ana',20],['Pedro',19]],
        [['Ana','Bases de datos',80.0],['Ana','Compiladores',90.0],['Luis','Compiladores',70.0],['María','Compiladores',95.0]],
        [[3,3,255.0,85.0,70.0,95.0]],
        [['Ana'],['Luis'],['María']],[['Pedro']],
        [['Ana'],['Luis'],['María']],[['Pedro']],[['María']]]
    for i,(output,want) in enumerate(zip(result['results'],expected),1):
        assert output['rows'] == want,(i,output,want)
        record(f'Consulta {i}: filtro/JOIN/agregación/subconsulta',output['rows'])
    assert len(result['results']) == len(expected)
    before = cli('before_index','execute','SELECT nombre FROM estudiantes WHERE 20=edad;')['results'][-1]
    result = cli('index_dml','execute',file='03_index.sql')
    outputs = result['results']
    after = outputs[1]
    assert before['rows'] == after['rows'] == [['Ana']]
    assert before['stats']['row_reads'] == 4 and before['stats']['table_scans'] == 1
    assert after['stats']['row_reads'] == 1 and after['stats']['table_scans'] == 0 and after['stats']['index_lookups'] == 1
    assert outputs[3]['rows'] == [['Ana',21]] and outputs[4]['rows'] == []
    assert outputs[6]['rows'] == [['Ana'],['Eva']] and outputs[8]['rows'] == [['Ana']]
    record('Índice antes/después y mantenimiento DML',{'before':before['stats'],'after':after['stats'],'post_update':outputs[3]['rows'],'post_insert':outputs[6]['rows'],'post_delete':outputs[8]['rows']})
    result = cli('reopen','execute',file='04_reopen.sql')
    assert result['results'][0]['rows'] == [['Ana',21]]
    assert result['results'][1]['rows'] == [[3,3],[4,1]]
    record('Persistencia en proceso nuevo',[r['rows'] for r in result['results']])

    errors = {
        'lexer': 'SELECT @ FROM estudiantes;',
        'parser': 'SELECT FROM estudiantes;',
        'table': 'SELECT * FROM inexistente;',
        'column': 'SELECT desconocida FROM estudiantes;',
        'ambiguous': 'SELECT id FROM estudiantes e INNER JOIN cursos c ON e.id=c.id;',
        'type': "UPDATE estudiantes SET edad='veinte' WHERE id=1;",
        'date': "UPDATE estudiantes SET nacimiento=DATE '2023-02-29' WHERE id=1;",
        'varchar': "UPDATE estudiantes SET nombre='123456789012345678901' WHERE id=1;",
        'not_null': 'UPDATE estudiantes SET nombre=NULL WHERE id=1;',
        'primary_key': "INSERT INTO cursos VALUES(5,'X'),(3,'Duplicado');",
        'index_duplicate': 'CREATE INDEX idx_edad ON estudiantes(edad);',
        'index_missing': 'DROP INDEX inexistente;',
        'scalar_columns': 'SELECT * FROM estudiantes WHERE edad=(SELECT id,edad FROM estudiantes);',
        'scalar_rows': 'SELECT * FROM estudiantes WHERE edad=(SELECT edad FROM estudiantes);',
    }
    for name,sql in errors.items():
        old = snapshot()
        result = cli(f'error_{name}','execute',sql,accepted=False)
        assert snapshot() == old,name
        error = result['diagnostics'][0]
        assert error['location']['line'] >= 1 and error['location']['column'] >= 1
        record(f'Error controlado: {name}',error)
    old = snapshot()
    result = cli('scalar_analysis','analyze',file='error_scalar.sql',accepted=False)
    assert snapshot() == old
    record('Cardinalidad escalar en Analizar',result['diagnostics'][0])

    code = '''
import json
from sql_interpreter.storage import FileStorage
from sql_interpreter.api import execute_sql
s=FileStorage('database')
original=s.scan
def blocked(table):
    if table=='estudiantes': raise AssertionError('recorrido exterior oculto')
    return original(table)
s.scan=blocked
r=execute_sql('SELECT nombre FROM estudiantes WHERE edad=21;',s)
assert r.accepted and r.results[-1].rows==[['Ana']]
print(json.dumps(r.results[-1].stats))
'''
    p = process([str(python),'-I','-B','-c',code])
    assert p.returncode == 0,p.stderr
    record('Recuperación por índice con scan prohibido',json.loads(p.stdout))
    cli('cleanup','execute',file='05_cleanup.sql')
    record('DROP INDEX y CREATE/INSERT/DROP TABLE','Aceptados; tablas principales conservadas')

    gui = '''
import json,os,time
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase,QFont
from sql_interpreter.gui import MainWindow
app=QApplication([])
for f in ['arial.ttf','consola.ttf']:
    p=Path('C:/Windows/Fonts')/f
    if p.exists(): QFontDatabase.addApplicationFont(str(p))
app.setFont(QFont('Arial',10))
w=MainWindow('gui_database')
def wait():
    end=time.monotonic()+30
    while w.worker is not None and time.monotonic()<end: app.processEvents()
    assert w.worker is None,'GUI timeout'
w.editor.setPlainText('CREATE TABLE demo(id INT); INSERT INTO demo VALUES(7); SELECT * FROM demo;')
w.show();w.start_analysis();wait()
assert not Path('gui_database').exists()
assert w.tokens.rowCount()>0 and w.tree.topLevelItemCount()>0 and w.ast_tree.topLevelItemCount()>0
w.start_execution();wait()
assert w.results.item(0,0).text()=='7'
app.processEvents();w.grab().save('gui_results.png')
w.tabs.setCurrentIndex(2);app.processEvents();w.grab().save('gui_ast.png')
print(json.dumps({'tokens':w.tokens.rowCount(),'tree':w.tree.topLevelItemCount(),'ast':w.ast_tree.topLevelItemCount(),'result':'7'}))
w.editor.document().setModified(False);w.close()
'''
    p = process([str(python),'-I','-B','-c',gui])
    (stage/'gui.stderr.txt').write_text(p.stderr,encoding='utf-8')
    assert p.returncode == 0,p.stdout+p.stderr
    record('GUI instalada: analizar/ejecutar/vistas',json.loads(p.stdout))

    p = process([str(python),'-I','-B','-m','pytest',str(ROOT/'tests'),'-c',str(ROOT/'pyproject.toml'),'-o','pythonpath=','-q','--tb=short'])
    (stage/'pytest.txt').write_text(p.stdout+p.stderr,encoding='utf-8')
    assert p.returncode == 0,p.stdout+p.stderr
    summary = re.search(r'\d+ passed[^\n]*',p.stdout)
    record('Suite completa contra paquete instalado',summary.group(0) if summary else p.stdout[-500:])
    report = {'timestamp':datetime.now().astimezone().isoformat(),'stage':str(stage),'database':str(db),
              'installation':'venv sin paquetes globales; dependencias copiadas de distribuciones locales por bloqueo de PyPI',
              'environment':environment,'checks':cases,'passed':len(cases),'failed':0}
    (stage/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'tmp/latest-presentation-run.txt').write_text(str(stage),encoding='utf-8')
    print(json.dumps({'stage':str(stage),'checks_passed':len(cases),'pytest':cases[-1]['details']},ensure_ascii=False))


if __name__ == '__main__':
    main()

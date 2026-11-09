"""Instala un wheel en tmp y verifica CLI, persistencia y análisis sin escrituras.

Uso: py scripts/verify_install.py tmp/wheels/sql_interpreter_files-1.0.0-py3-none-any.whl
No usa el árbol src como ruta de importación del proceso verificado.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    wheel = Path(sys.argv[1]).resolve()
    (root/'tmp').mkdir(exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix='installed-',dir=root/'tmp'))
    target = sandbox/'package'
    subprocess.run([sys.executable,'-m','pip','install','--no-deps','--no-index','--target',str(target),str(wheel)],check=True)
    env = os.environ | {'PYTHONPATH':str(target),'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'}
    database = sandbox/'database'

    def cli(action,file):
        result = subprocess.run([sys.executable,'-B','-m','sql_interpreter',action,str(file),'--database',str(database),'--json'],cwd=sandbox,env=env,capture_output=True,text=True,encoding='utf-8')
        if result.returncode: raise AssertionError(result.stderr or result.stdout)
        return json.loads(result.stdout)

    assert cli('analyze',root/'examples/demo.sql')['accepted']
    assert not database.exists()
    result = cli('execute',root/'examples/demo.sql')
    assert result['results'][-1]['rows'] == [['Ana',21],['María',22]]
    assert cli('execute',root/'examples/queries.sql')['accepted']
    code = '''
import os,sys
from sql_interpreter.api import analyze_sql,execute_sql
from sql_interpreter.storage import FileStorage
def audit(event,args):
    if event == 'open':
        flags = args[2]
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            raise AssertionError('analysis opened a file for writing')
sys.addaudithook(audit)
assert analyze_sql('CREATE TABLE t(id INT); INSERT INTO t VALUES(1); SELECT * FROM t;').accepted
store = FileStorage('database')
drop = analyze_sql('DROP TABLE estudiantes;',storage=store)
assert not drop.accepted and 'inscripciones' in drop.diagnostics[0].message
assert not analyze_sql('SELECT * FROM estudiantes WHERE edad=(SELECT edad FROM estudiantes);',storage=store).accepted
query = execute_sql('SELECT nombre FROM estudiantes WHERE -1<edad;',store)
assert query.accepted
assert query.results[-1].stats['index_lookups'] == 1
assert query.results[-1].stats['table_scans'] == 0
'''
    subprocess.run([sys.executable,'-B','-c',code],cwd=sandbox,env=env,check=True)
    print('Instalación autónoma, CLI, reapertura y análisis sin escrituras: OK')


if __name__ == '__main__':
    main()

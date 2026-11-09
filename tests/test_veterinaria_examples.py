"""Ejecuta exactamente los SQL de la carpeta que se utilizará en la presentación."""
from pathlib import Path

from sql_interpreter.api import analyze_sql, execute_sql
from sql_interpreter.storage import FileStorage

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples/veterinaria'


def test_complete_veterinary_presentation(tmp_path):
    db = FileStorage(tmp_path/'veterinaria')
    def run(name):
        result = execute_sql((EXAMPLES/name).read_text(encoding='utf-8'),db)
        assert result.accepted,(name,result.diagnostics)
        return result.results

    assert analyze_sql((EXAMPLES/'01_crear_datos.sql').read_text(encoding='utf-8')).accepted
    assert not db.root.exists()
    run('01_crear_datos.sql')
    results = run('02_consultas.sql')
    expected = [
        [['Coco',8],['Milo',2],['Nina',1]],
        [[1,'Luna','Marta',150.0],[2,'Luna','Marta',200.0],[3,'Milo','Diego',120.0]],
        [['Luna',2,350.0,175.0,150.0,200.0]],
        [['Luna'],['Milo']],[['Coco'],['Nina']],
        [['Luna'],['Milo']],[['Coco'],['Nina']],
        [['Coco',8]],[[2,200.0]],[[2,'2026-10-05',200.0]],[['Coco']],[[4,3]],
    ]
    assert [r.rows for r in results] == expected
    before = run('03_busqueda_sin_indice.sql')[-1]
    after = run('04_crear_indice.sql')[-1]
    assert before.rows == after.rows == [['Milo']]
    assert before.stats['row_reads'] == 4 and before.stats['table_scans'] == 1
    assert after.stats['row_reads'] == 1 and after.stats['table_scans'] == 0
    changes = run('05_cambios.sql')
    assert changes[1].rows == []
    assert changes[2].rows == [['Milo',3,True]]
    assert changes[4].rows == [['Milo'],['Toby']]
    assert changes[6].rows == [['Milo']]
    db = FileStorage(db.root)
    assert [r.rows for r in run('06_reabrir.sql')] == [[['Milo',3,True]],[[4]]]
    for path in sorted((EXAMPLES/'errores').glob('*.sql')):
        old = {p:p.read_bytes() for p in db.root.rglob('*') if p.is_file()}
        result = execute_sql(path.read_text(encoding='utf-8'),db)
        assert not result.accepted,path.name
        assert {p:p.read_bytes() for p in db.root.rglob('*') if p.is_file()} == old,path.name
    run('07_eliminar_indice_y_tabla_temporal.sql')
    assert 'recordatorios' not in db.catalog['tables']
    assert not db.catalog['indexes']
    run('08_borrado_ordenado_OPCIONAL.sql')
    assert db.catalog['tables'] == {}

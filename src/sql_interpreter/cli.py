"""CLI y serialización compartida con la GUI."""
import argparse
from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
import sys
from .api import analyze_sql, execute_sql
from .storage import FileStorage
from .models import SqlError


def serialize(value):
    if is_dataclass(value):
        return {name:serialize(getattr(value,name)) for name,field in value.__dataclass_fields__.items() if field.repr}
    if isinstance(value,(list,tuple)): return [serialize(v) for v in value]
    if isinstance(value,dict): return {k:serialize(v) for k,v in value.items()}
    return value


def payload(result):
    return {'accepted':result.accepted, 'tokens':serialize(result.syntax.tokens),
            'tree':serialize(result.syntax.tree), 'ast':serialize(result.ast),
            'diagnostics':serialize(result.diagnostics), 'results':serialize(result.results)}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Intérprete SQL con archivos propios')
    parser.add_argument('action',choices=['analyze','execute','gui'])
    parser.add_argument('file',nargs='?',help='Archivo SQL UTF-8; - para stdin')
    parser.add_argument('--database',default='database',help='Directorio del almacenamiento')
    parser.add_argument('--json',action='store_true',help='Salida estructurada')
    args = parser.parse_args(argv)
    if args.action == 'gui':
        from .gui import launch
        return launch(args.database)
    if not args.file:
        parser.error('analyze y execute requieren un archivo SQL o -')
    try:
        source = sys.stdin.read() if args.file == '-' else Path(args.file).read_text(encoding='utf-8-sig')
        storage = FileStorage(args.database)
        result = analyze_sql(source,storage.catalog,args.file,storage=storage) if args.action == 'analyze' else execute_sql(source,storage,args.file)
        if args.json:
            print(json.dumps(payload(result),ensure_ascii=False,allow_nan=False))
        else:
            for diagnostic in result.diagnostics:
                at = diagnostic.location
                print(f'{diagnostic.stage} {at.line}:{at.column}: {diagnostic.message}')
            for output in result.results:
                if output.kind == 'select':
                    print(' | '.join(output.columns))
                    for row in output.rows: print(' | '.join('NULL' if v is None else str(v) for v in row))
                else: print(f'{output.kind}: {output.affected} filas')
            if args.action == 'analyze' and result.accepted: print('Análisis correcto')
        return 0 if result.accepted else 1
    except (OSError,UnicodeError,SqlError) as exc:
        print(str(exc),file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

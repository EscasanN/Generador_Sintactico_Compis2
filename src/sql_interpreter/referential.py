"""Validación de referencias del catálogo, sin leer archivos ni ejecutar SQL."""


def validate_reference(catalog, table, reference):
    fields = ('column', 'referenced_table', 'referenced_column')
    if not isinstance(reference, dict) or not all(isinstance(reference.get(f), str) for f in fields):
        raise ValueError('Definición de llave foránea inválida')
    columns = {c['name']: c for c in catalog['tables'][table]['columns']}
    if reference['column'] not in columns:
        raise ValueError(f"Columna inexistente para llave foránea: {reference['column']}")
    parent_name = reference['referenced_table']
    if parent_name not in catalog['tables']:
        raise ValueError(f'Tabla referenciada inexistente: {parent_name}')
    target = {c['name']: c for c in catalog['tables'][parent_name]['columns']}
    if reference['referenced_column'] not in target:
        raise ValueError(f"Columna referenciada inexistente: {parent_name}.{reference['referenced_column']}")
    source, parent = columns[reference['column']], target[reference['referenced_column']]
    if not set(parent['constraints']) & {'PRIMARY KEY', 'UNIQUE'}:
        raise ValueError('La columna referenciada requiere PRIMARY KEY o UNIQUE')
    if (source['type'], source.get('size')) != (parent['type'], parent.get('size')):
        raise ValueError('Tipos incompatibles en la llave foránea y su referencia')

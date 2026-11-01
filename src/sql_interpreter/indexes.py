"""Índices persistibles: claves tipadas y referencias directas de fila."""
import json


def key(value):
    # bool debe distinguirse de int, aunque Python los compara como iguales.
    if type(value) in (int,float):
        # 2 y 2.0 son iguales en el dominio SQL numérico, sin redondear enteros.
        value = int(value) if value == int(value) else value
        tag = 'number'
    else:
        tag = type(value).__name__
    return json.dumps([tag, value], ensure_ascii=False, separators=(',', ':'))


def build_index(rows, column):
    entries = {}
    for rid, row in rows.items():
        entries.setdefault(key(row[column]), []).append(rid)
    return entries


def lookup(entries, op, value):
    if value is None:
        return []
    if op == '=':
        return entries.get(key(value), [])
    found = []
    for encoded, ids in entries.items():
        _, candidate = json.loads(encoded)
        if candidate is None:
            continue
        matches = {'<': lambda: candidate < value, '<=': lambda: candidate <= value,
                   '>': lambda: candidate > value, '>=': lambda: candidate >= value,
                   '!=': lambda: candidate != value, '<>': lambda: candidate != value}
        if matches[op]():
            found.extend(ids)
    return found

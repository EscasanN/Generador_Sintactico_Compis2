"""Generaciones inmutables con referencias directas a filas e índices compartidos.

Lee formatos 1 y 2. Publica formato 2 sin copiar filas ajenas al cambio.
"""
from copy import deepcopy
from datetime import date
import json
import math
import os
from pathlib import Path
import re
from uuid import uuid4
from .indexes import build_index, key, lookup
from .models import MAX_INTEGER, SqlError


class FileStorage:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.reset_stats()
        self.refresh()

    def reset_stats(self):
        self.stats = {'row_reads': 0, 'table_scans': 0, 'index_lookups': 0,
                      'row_writes': 0, 'index_writes': 0}

    @staticmethod
    def _error(path, detail):
        return SqlError(f'Almacenamiento ilegible en {path}: {detail}', stage='STORAGE')

    @staticmethod
    def _component(value):
        return isinstance(value, str) and re.fullmatch(r'[a-zA-Z0-9_-]+', value) is not None

    @classmethod
    def _read(cls, path):
        def invalid_constant(value):
            raise ValueError(f'Constante JSON inválida: {value}')
        try:
            return json.loads(path.read_text(encoding='utf-8'), parse_constant=invalid_constant)
        except (OSError, UnicodeError, ValueError) as exc:
            raise cls._error(path, str(exc)) from exc

    def refresh(self):
        self.generation = None
        self.catalog = {'tables': {}, 'indexes': {}}
        self.row_ids = {}
        self.row_generations = {}
        self.index_generations = {}
        manifest_path = self.root / 'manifest.json'
        if not manifest_path.exists():
            return
        manifest = self._read(manifest_path)
        if (not isinstance(manifest, dict) or manifest.get('format') not in (1, 2)
                or not self._component(manifest.get('generation'))):
            raise self._error(manifest_path, 'formato o generación inválidos')
        owner = manifest['generation']
        generation = self.root / 'generations' / owner
        catalog_path = generation / 'catalog.json'
        catalog = self._read(catalog_path)
        if (not isinstance(catalog, dict) or not isinstance(catalog.get('tables'), dict)
                or not isinstance(catalog.get('indexes'), dict)):
            raise self._error(catalog_path, 'catálogo inválido')
        for table, schema in catalog['tables'].items():
            if (not self._component(table) or not isinstance(schema, dict)
                    or not isinstance(schema.get('columns'), list)):
                raise self._error(catalog_path, 'esquema de tabla inválido')
            names = set()
            for column in schema['columns']:
                if (not isinstance(column, dict) or not self._component(column.get('name'))
                        or column.get('name') in names
                        or column.get('type') not in ('INT','FLOAT','VARCHAR','DATE','BOOLEAN')
                        or not isinstance(column.get('constraints'), list)
                        or any(c not in ('NOT NULL','UNIQUE','PRIMARY KEY') for c in column['constraints'])
                        or (column['type'] == 'VARCHAR' and
                            (type(column.get('size')) is not int or column['size'] <= 0))):
                    raise self._error(catalog_path, 'definición de columna inválida')
                names.add(column['name'])
        for name, index in catalog['indexes'].items():
            if (not self._component(name) or not isinstance(index, dict)
                    or not self._component(index.get('table'))
                    or not self._component(index.get('column'))
                    or index.get('table') not in catalog['tables']
                    or index.get('column') not in {c['name'] for c in catalog['tables'][index['table']]['columns']}):
                raise self._error(catalog_path, 'definición de índice inválida')
        rows_path = generation / 'rows.json'
        rows = self._read(rows_path)
        if not isinstance(rows, dict) or rows.keys() != catalog['tables'].keys():
            raise self._error(rows_path, 'directorio de filas inválido')
        refs = {}
        for table, entries in rows.items():
            if manifest['format'] == 1:
                if not isinstance(entries, list) or not all(self._component(rid) for rid in entries) or len(set(entries)) != len(entries):
                    raise self._error(rows_path, 'lista de RID inválida')
                entries = dict.fromkeys(entries, owner)
            if not isinstance(entries, dict) or not all(self._component(rid) and self._component(g) for rid, g in entries.items()):
                raise self._error(rows_path, 'referencias de fila inválidas')
            refs[table] = entries
        if manifest['format'] == 1:
            index_refs = dict.fromkeys(catalog['indexes'], owner)
        else:
            index_path = generation / 'indexes.json'
            index_refs = self._read(index_path)
            if (not isinstance(index_refs, dict) or index_refs.keys() != catalog['indexes'].keys()
                    or not all(self._component(g) for g in index_refs.values())):
                raise self._error(index_path, 'referencias de índice inválidas')
        self.generation, self.catalog = generation, catalog
        self.row_generations, self.index_generations = refs, index_refs
        self.row_ids = {table: list(entries) for table, entries in refs.items()}

    @staticmethod
    def _write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())

    def scan(self, table):
        self.stats['table_scans'] += 1
        return self.fetch(table, self.row_ids.get(table, []))

    @staticmethod
    def _valid_value(column, value, index_key=False):
        typ = column['type']
        if value is None:
            return not set(column['constraints']) & {'NOT NULL', 'PRIMARY KEY'}
        if typ == 'INT':
            return type(value) is int and abs(value) <= MAX_INTEGER
        if typ == 'FLOAT':
            try:
                return (type(value) is float or (index_key and type(value) is int)) and math.isfinite(value)
            except OverflowError:
                return False
        if typ == 'BOOLEAN':
            return type(value) is bool
        if not isinstance(value, str):
            return False
        if typ == 'VARCHAR':
            return len(value) <= column['size']
        try:
            return re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) is not None and date.fromisoformat(value) is not None
        except ValueError:
            return False

    def fetch(self, table, ids):
        result = []
        columns = self.catalog['tables'][table]['columns']
        for rid in ids:
            rid = str(rid)
            if rid not in self.row_generations.get(table, {}):
                raise self._error(self.generation / 'rows.json', f'RID inexistente: {table}/{rid}')
            owner = self.row_generations[table][rid]
            path = self.root / 'generations' / owner / 'tables' / table / f'{rid}.json'
            self.stats['row_reads'] += 1
            row = self._read(path)
            if not isinstance(row, dict) or row.keys() != {c['name'] for c in columns}:
                raise self._error(path, 'la fila no coincide con su esquema')
            for column in columns:
                value, typ = row[column['name']], column['type']
                if not self._valid_value(column, value):
                    raise self._error(path, f"valor inválido para {column['name']} ({typ})")
            result.append((rid, row))
        return result

    def _load_index(self, index):
        path = self.root / 'generations' / self.index_generations[index] / 'indexes' / f'{index}.json'
        entries = self._read(path)
        if not isinstance(entries, dict):
            raise self._error(path, 'índice inválido')
        try:
            table = self.catalog['indexes'][index]['table']
            column_name = self.catalog['indexes'][index]['column']
            column = next(c for c in self.catalog['tables'][table]['columns'] if c['name'] == column_name)
            seen = set()
            for encoded, ids in entries.items():
                decoded = json.loads(encoded)
                if (not isinstance(decoded, list) or len(decoded) != 2 or key(decoded[1]) != encoded
                        or not self._valid_value(column, decoded[1], index_key=True)
                        or not isinstance(ids, list) or any(not isinstance(rid, str) or rid not in self.row_generations[table] for rid in ids)):
                    raise ValueError('entrada de índice inválida')
                if any(rid in seen for rid in ids) or len(set(ids)) != len(ids):
                    raise ValueError('RID duplicado en índice')
                seen.update(ids)
            if seen != self.row_generations[table].keys():
                raise ValueError('el índice no cubre los RID de la tabla')
        except (TypeError, ValueError, OverflowError) as exc:
            raise self._error(path, str(exc)) from exc
        return entries

    def lookup(self, index, op, value):
        self.stats['index_lookups'] += 1
        entries = self._load_index(index)
        try:
            return lookup(entries, op, value)
        except (TypeError, ValueError) as exc:
            path = self.root / 'generations' / self.index_generations[index] / 'indexes' / f'{index}.json'
            raise self._error(path, str(exc)) from exc

    def snapshot(self):
        return {name: dict(self.scan(name)) for name in self.catalog['tables']}

    def _publish(self, manifest, temp):
        os.replace(temp, manifest)

    def commit(self, catalog, tables):
        """Reemplazo completo explícito, conservado para clientes del formato 1."""
        changes = {}
        for table in catalog['tables']:
            rows = tables.get(table, {})
            changes[table] = dict.fromkeys(self.row_ids.get(table, []), None) | rows
        self.commit_changes(catalog, changes)

    def commit_changes(self, catalog, changes):
        """Publica RID -> nueva fila/None; las filas no mencionadas se comparten."""
        generation = uuid4().hex
        target = self.root / 'generations' / generation
        refs = {table: dict(self.row_generations.get(table, {})) for table in catalog['tables']}
        for table, edits in changes.items():
            for rid, row in edits.items():
                if row is None:
                    refs[table].pop(rid, None)
                else:
                    refs[table][rid] = generation
        # Preparar índices antes de escribir: corrupción no deja cambios preparados.
        index_refs, prepared = {}, {}
        for name, index in catalog['indexes'].items():
            table, column = index['table'], index['column']
            edits = changes.get(table, {})
            if name not in self.catalog['indexes'] or self.catalog['indexes'][name] != index:
                rows = dict(self.scan(table)) if table in self.catalog['tables'] else {}
                for rid, row in edits.items():
                    if row is None: rows.pop(rid, None)
                    else: rows[rid] = row
                prepared[name] = build_index(rows, column)
            elif edits:
                entries = self._load_index(name)
                entries = {encoded: [rid for rid in ids if rid not in edits] for encoded, ids in entries.items()}
                entries = {encoded: ids for encoded, ids in entries.items() if ids}
                for rid, row in edits.items():
                    if row is not None:
                        entries.setdefault(key(row[column]), []).append(rid)
                prepared[name] = entries
            else:
                index_refs[name] = self.index_generations[name]
        index_refs.update(dict.fromkeys(prepared, generation))
        self._write(target / 'catalog.json', catalog)
        self._write(target / 'rows.json', refs)
        self._write(target / 'indexes.json', index_refs)
        for table, edits in changes.items():
            for rid, row in edits.items():
                if row is not None:
                    self._write(target / 'tables' / table / f'{rid}.json', row)
                    self.stats['row_writes'] += 1
        for name, entries in prepared.items():
            self._write(target / 'indexes' / f'{name}.json', entries)
            self.stats['index_writes'] += 1
        temporary = self.root / f'manifest-{generation}.tmp'
        self._write(temporary, {'generation': generation, 'format': 2})
        self._publish(self.root / 'manifest.json', temporary)
        self.generation, self.catalog = target, deepcopy(catalog)
        self.row_generations, self.index_generations = refs, index_refs
        self.row_ids = {table: list(entries) for table, entries in refs.items()}

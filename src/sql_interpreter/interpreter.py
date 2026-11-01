"""Evaluación SQL independiente de Qt y del frontend ANTLR."""
from copy import deepcopy
from dataclasses import dataclass, field
import operator
import math
from uuid import uuid4
from .models import SqlError,MAX_INTEGER
from .semantic import fail, has_aggregate, validate_value
from .planning import correlated, expressions


@dataclass
class StatementResult:
    kind: str
    columns: list[str] = field(default_factory=list)
    rows: list[list] = field(default_factory=list)
    affected: int = 0
    stats: dict = field(default_factory=dict)


def sql_not(value):
    return None if value is None else not value


def finite(value,e):
    if type(value) is int and abs(value) > MAX_INTEGER:
        raise SqlError('Resultado INT excede el límite de 4096 dígitos',e.location,'EXECUTION')
    if isinstance(value,float) and not math.isfinite(value):
        raise SqlError('Resultado FLOAT fuera de rango',e.location,'EXECUTION')
    return value


class Interpreter:
    def __init__(self, storage):
        self.storage = storage
        self.query_cache = {}

    def query_result(self, query, envs, existence_only=False):
        reusable = not correlated(query, self.storage.catalog)
        key = (id(query), existence_only)
        if reusable and key in self.query_cache:
            return self.query_cache[key]
        result = self.select(query, envs, existence_only=existence_only)
        if reusable:
            self.query_cache[key] = result
        return result

    def preflight(self, stmt):
        scalars = [e for e in expressions(stmt) if e.kind == 'scalar']
        if not scalars:
            return
        for e in scalars:
            if not correlated(e.query, self.storage.catalog):
                self.evaluate(e, [])
        # Las correlacionadas requieren los contextos de las filas exteriores.
        if stmt.kind == 'select':
            self.select(stmt, existence_only=True)
        elif stmt.kind in ('update', 'delete'):
            from .ast import TableRef
            ref = TableRef(stmt.table, stmt.table, stmt.location)
            for _, row in self.candidates(ref, stmt.where):
                if stmt.where:
                    self.evaluate(stmt.where, [{stmt.table: row}])

    def evaluate(self, e, envs, group=None):
        if e.kind == 'literal': return e.value
        if e.kind == 'column':
            for env in envs:
                if e.qualifier:
                    if e.qualifier in env: return env[e.qualifier][e.name]
                else:
                    values = [row[e.name] for row in env.values() if e.name in row]
                    if values: return values[0]
            fail('Columna no disponible durante evaluación',e)
        if e.kind in ('scalar','in','exists'):
            result = self.query_result(e.query,envs,existence_only=e.kind == 'exists')
            if e.kind == 'exists': return bool(result.rows)
            if e.kind == 'scalar':
                if len(result.rows) > 1: fail('Subconsulta escalar retornó más de una fila',e)
                return result.rows[0][0] if result.rows else None
            value = self.evaluate(e.left,envs,group)
            values = [row[0] for row in result.rows]
            answer = False if not values else None if value is None else True if value in values else None if None in values else False
            return sql_not(answer) if e.op == 'NOT IN' else answer
        if e.kind == 'aggregate':
            rows = group or []
            if e.left.kind == 'star': return len(rows)
            values = [self.evaluate(e.left,[row] + envs[1:]) for row in rows]
            values = [v for v in values if v is not None]
            if e.name == 'COUNT': return len(values)
            if not values: return None
            try:
                if e.name == 'SUM': return finite(sum(values),e)
                if e.name == 'AVG': return finite(sum(values)/len(values),e)
            except OverflowError as exc:
                raise SqlError('Resultado numérico fuera de rango',e.location,'EXECUTION') from exc
            return min(values) if e.name == 'MIN' else max(values)
        left = self.evaluate(e.left,envs,group)
        if e.kind == 'is_null': return (left is not None) if e.op == 'IS NOT NULL' else (left is None)
        if e.kind == 'unary':
            if e.op == 'NOT': return sql_not(left)
            if left is None: return None
            return -left if e.op == '-' else left
        right = self.evaluate(e.right,envs,group)
        if e.op == 'AND':
            return False if left is False or right is False else None if left is None or right is None else True
        if e.op == 'OR':
            return True if left is True or right is True else None if left is None or right is None else False
        if left is None or right is None: return None
        operations = {'=':operator.eq, '<>':operator.ne, '!=':operator.ne, '<':operator.lt, '<=':operator.le,
                      '>':operator.gt, '>=':operator.ge, '+':operator.add, '-':operator.sub, '*':operator.mul, '/':operator.truediv}
        try:
            return finite(operations[e.op](left,right),e)
        except (ZeroDivisionError, OverflowError, ValueError) as exc:
            raise SqlError(f'Error al evaluar {e.op}: {exc}',e.location,'EXECUTION') from exc

    def candidates(self, ref, where):
        # AND puede reducir candidatos; OR requiere una estrategia completa.
        if where and where.kind == 'binary' and where.op == 'AND':
            left = self.index_candidate(ref,where.left)
            if left is not None: return self.storage.fetch(ref.name,left)
            right = self.index_candidate(ref,where.right)
            if right is not None: return self.storage.fetch(ref.name,right)
        ids = self.index_candidate(ref,where)
        return self.storage.scan(ref.name) if ids is None else self.storage.fetch(ref.name,ids)

    def index_candidate(self,ref,e):
        if not e: return None
        if e.kind == 'binary' and e.op == 'AND':
            left = self.index_candidate(ref,e.left)
            return left if left is not None else self.index_candidate(ref,e.right)
        if e.kind == 'binary' and e.op == 'OR':
            left,right = self.index_candidate(ref,e.left),self.index_candidate(ref,e.right)
            return list(dict.fromkeys(left+right)) if left is not None and right is not None else None
        if e.kind == 'in' and not correlated(e.query, self.storage.catalog):
            column = e.left
            if column.kind != 'column' or (column.qualifier and column.qualifier != ref.alias):
                return None
            for name, index in self.storage.catalog['indexes'].items():
                if index['table'] == ref.name and index['column'] == column.name:
                    values = list(dict.fromkeys(row[0] for row in self.query_result(e.query, []).rows))
                    if e.op == 'NOT IN':
                        if None in values: return []
                        ids = set(self.storage.row_ids[ref.name])
                        for value in values:
                            ids.intersection_update(self.storage.lookup(name, '!=', value))
                        return [rid for rid in self.storage.row_ids[ref.name] if rid in ids]
                    ids = []
                    for value in values:
                        if value is not None:
                            ids.extend(self.storage.lookup(name, '=', value))
                    return list(dict.fromkeys(ids))
            return None
        if e.kind != 'binary' or e.op not in ('=','!=','<>','<','<=','>','>='): return None
        column, literal, op = e.left,e.right,e.op
        if literal.kind == 'column' and self.constant(column):
            column,literal = literal,column
            op = {'=':'=','!=':'!=','<>':'<>','<':'>','<=':'>=','>':'<','>=':'<='}[op]
        constant = self.constant(literal)
        if column.kind != 'column' or not constant: return None
        if column.qualifier and column.qualifier != ref.alias: return None
        if not column.qualifier and column.name not in {c['name'] for c in self.storage.catalog['tables'][ref.name]['columns']}: return None
        for name,index in self.storage.catalog['indexes'].items():
            if index['table'] == ref.name and index['column'] == column.name:
                return self.storage.lookup(name,op,self.evaluate(literal,[]))
        return None

    def constant(self, e):
        if e.kind == 'literal': return True
        if e.kind == 'unary' and e.op in ('+', '-'): return self.constant(e.left)
        return e.kind == 'scalar' and not correlated(e.query, self.storage.catalog)

    def select(self,stmt,outer=None,existence_only=False):
        outer = outer or []
        # En consultas con JOIN, no inferir a qué tabla pertenece una columna sin calificar.
        predicate = stmt.where
        rows = [{stmt.table.alias:row} for _,row in self.candidates(stmt.table,predicate)]
        for ref,on in stmt.joins:
            joined = []
            right = self.candidates(ref,predicate)
            for left in rows:
                for _,row in right:
                    combined = left | {ref.alias:row}
                    if self.evaluate(on,[combined]+outer) is True: joined.append(combined)
            rows = joined
        if stmt.where:
            rows = [row for row in rows if self.evaluate(stmt.where,[row]+outer) is True]
        grouped = bool(stmt.group_by) or any(has_aggregate(i.expr) for i in stmt.items) or has_aggregate(stmt.having) or any(has_aggregate(e) for e,_ in stmt.order_by)
        if stmt.group_by:
            groups = {}
            for row in rows:
                key = tuple(self.evaluate(e,[row]+outer) for e in stmt.group_by)
                groups.setdefault(key,[]).append(row)
            batches = list(groups.values())
        else:
            batches = [rows] if grouped else [[row] for row in rows]
        refs = [stmt.table] + [r for r,_ in stmt.joins]
        columns = []
        for item in stmt.items:
            if item.expr.kind == 'star':
                for ref in refs:
                    if not item.expr.qualifier or item.expr.qualifier == ref.alias:
                        columns.extend(c['name'] for c in self.storage.catalog['tables'][ref.name]['columns'])
            else: columns.append(item.alias or item.expr.name or item.expr.op or 'expr')
        output = []
        for batch in batches:
            env = batch[0] if batch else {}
            envs = [env]+outer
            group = batch if grouped else None
            if stmt.having and self.evaluate(stmt.having,envs,group) is not True: continue
            if existence_only:
                return StatementResult('select',rows=[[]])
            values = []
            aliases = {}
            for item in stmt.items:
                if item.expr.kind == 'star':
                    for ref in refs:
                        if not item.expr.qualifier or item.expr.qualifier == ref.alias:
                            values.extend(env[ref.alias][c['name']] for c in self.storage.catalog['tables'][ref.name]['columns'])
                else:
                    value = self.evaluate(item.expr,envs,group)
                    values.append(value)
                    if item.alias: aliases[item.alias] = value
            keys = []
            for e,_ in stmt.order_by:
                keys.append(aliases[e.name] if e.kind == 'column' and not e.qualifier and e.name in aliases else self.evaluate(e,envs,group))
            output.append((values,keys))
        for i,(_,descending) in reversed(list(enumerate(stmt.order_by))):
            output.sort(key=lambda row: (row[1][i] is None,row[1][i]), reverse=descending)
        return StatementResult('select',columns,[row[0] for row in output])

    def execute(self, stmt, catalog):
        if stmt.kind == 'select':
            return self.select(stmt)
        edits = {}
        affected = 0
        if stmt.kind in ('insert', 'update', 'delete'):
            columns = catalog['tables'][stmt.table]['columns']
            if stmt.kind == 'insert':
                selected = stmt.columns or [c['name'] for c in columns]
                for expressions in stmt.rows:
                    row = dict.fromkeys(c['name'] for c in columns)
                    row.update({name: self.evaluate(e, []) for name, e in zip(selected, expressions)})
                    for c in columns:
                        row[c['name']] = validate_value(row[c['name']], c, stmt)
                    edits[uuid4().hex] = row
            else:
                from .ast import TableRef
                ref = TableRef(stmt.table, stmt.table, stmt.location)
                for rid, row in self.candidates(ref, stmt.where):
                    envs = [{stmt.table: row}]
                    if stmt.where and self.evaluate(stmt.where, envs) is not True:
                        continue
                    if stmt.kind == 'delete':
                        edits[rid] = None
                    else:
                        new = row | {name: self.evaluate(e, envs) for name, e in stmt.assignments}
                        for c in columns:
                            new[c['name']] = validate_value(new[c['name']], c, stmt)
                        edits[rid] = new
            affected = len(edits)
            changed_columns = {name for name, _ in stmt.assignments}
            unique_columns = [c for c in columns
                              if set(c['constraints']) & {'UNIQUE', 'PRIMARY KEY'}
                              and (stmt.kind == 'insert' or
                                   (stmt.kind == 'update' and c['name'] in changed_columns))]
            if edits and unique_columns:
                # Solo la tabla afectada; primero el estado final para admitir swaps.
                final_rows = [row for rid, row in self.storage.scan(stmt.table) if rid not in edits]
                final_rows.extend(row for row in edits.values() if row is not None)
                for c in unique_columns:
                    seen = set()
                    for row in final_rows:
                        value = row[c['name']]
                        if value is not None:
                            if value in seen:
                                fail(f"Restricción UNIQUE/PRIMARY KEY en {c['name']}", stmt)
                            seen.add(value)
            if not edits:
                return StatementResult(stmt.kind, affected=0)
        changes = {stmt.table: edits} if edits else {}
        self.storage.commit_changes(catalog, changes)
        return StatementResult(stmt.kind, affected=affected)

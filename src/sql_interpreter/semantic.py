"""Resolución de nombres, tipos y reglas SQL sobre catálogo en memoria."""
from copy import deepcopy
from dataclasses import asdict
from datetime import date
import math
import re
from .ast import Expr
from .models import SqlError,MAX_INTEGER

NUMERIC = {'INT', 'FLOAT'}


def fail(message, node):
    raise SqlError(message, node.location)


def compatible(a, b):
    return a == b or 'NULL' in (a, b) or {a,b} <= NUMERIC


def assignable(target, source):
    return source == 'NULL' or target == source or (target == 'FLOAT' and source == 'INT')


def validate_value(value, column, node):
    if value is None:
        if set(column['constraints']) & {'NOT NULL','PRIMARY KEY'}:
            fail(f"La columna {column['name']} no admite NULL", node)
        return None
    typ = column['type']
    if type(value) is int and abs(value) > MAX_INTEGER:
        fail('INT excede el límite de 4096 dígitos',node)
    valid = {'INT':type(value) is int, 'FLOAT':type(value) in (int,float),
             'VARCHAR':isinstance(value,str), 'DATE':isinstance(value,str), 'BOOLEAN':type(value) is bool}[typ]
    if not valid:
        fail(f"Valor incompatible con {typ} en {column['name']}", node)
    if typ == 'FLOAT':
        try: value = float(value)
        except OverflowError: fail('FLOAT fuera de rango',node)
        if not math.isfinite(value): fail('FLOAT fuera de rango', node)
    if typ == 'VARCHAR' and len(value) > column['size']:
        fail(f"VARCHAR({column['size']}) excedido en {column['name']}", node)
    if typ == 'DATE':
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value): raise ValueError()
            date.fromisoformat(value)
        except ValueError:
            fail(f'Fecha inválida: {value}', node)
    return value


def resolve(expr, scopes):
    for scope in scopes:
        if expr.qualifier:
            if expr.qualifier not in scope:
                continue
            columns = scope[expr.qualifier]
            matches = [(expr.qualifier,c) for c in columns if c['name'] == expr.name]
            if not matches: fail(f'Columna inexistente: {expr.qualifier}.{expr.name}', expr)
        else:
            matches = [(a,c) for a, columns in scope.items() for c in columns if c['name'] == expr.name]
        if len(matches) > 1: fail(f'Columna ambigua: {expr.name}', expr)
        if matches: return matches[0]
    fail(f'Columna o alias inexistente: {expr.name}', expr)


def has_aggregate(e):
    return e is not None and (e.kind == 'aggregate' or has_aggregate(e.left) or has_aggregate(e.right))


def contains_query(e):
    return e is not None and (e.query is not None or contains_query(e.left) or contains_query(e.right))


def constant_value(e):
    if e.kind == 'literal': return True,e.value
    if e.kind == 'unary' and e.op in ('+','-') and e.left.kind == 'literal':
        value = e.left.value
        return True,None if value is None else -value if e.op == '-' else value
    return False,None


def signature(e):
    if e is None: return None
    return (e.kind,e.value,e.name,e.qualifier,e.op,signature(e.left),signature(e.right))


class SemanticAnalyzer:
    def __init__(self, catalog):
        self.catalog = deepcopy(catalog)

    def table(self, name, node):
        if name not in self.catalog['tables']: fail(f'Tabla inexistente: {name}', node)
        return self.catalog['tables'][name]['columns']

    def expression(self, e, scopes, aggregates=False):
        if e.kind == 'literal':
            if e.name == 'DATE': validate_value(e.value, {'name':'DATE','type':'DATE','constraints':[]}, e)
            if e.name == 'FLOAT' and not math.isfinite(e.value): fail('FLOAT fuera de rango', e)
            return e.name
        if e.kind == 'column': return resolve(e, scopes)[1]['type']
        if e.kind == 'star': fail('Comodín fuera de proyección o COUNT(*)', e)
        if e.kind in ('scalar','in','exists'):
            types = self.select(e.query, scopes)
            if e.kind != 'exists' and len(types) != 1: fail('La subconsulta requiere exactamente una columna', e)
            if e.kind == 'scalar': return types[0]
            if e.kind == 'in' and not compatible(self.expression(e.left,scopes,aggregates), types[0]): fail('Tipos incompatibles en IN', e)
            return 'BOOLEAN'
        if e.kind == 'aggregate':
            if not aggregates: fail('Agregación fuera de contexto o anidada', e)
            if e.left.kind == 'star':
                if e.name != 'COUNT': fail('Solo COUNT admite *', e)
                return 'INT'
            typ = self.expression(e.left,scopes,False)
            if e.name in ('SUM','AVG') and typ not in NUMERIC | {'NULL'}: fail('SUM/AVG requiere números', e)
            return 'INT' if e.name == 'COUNT' else 'FLOAT' if e.name == 'AVG' else typ
        left = self.expression(e.left, scopes, aggregates)
        if e.kind == 'is_null': return 'BOOLEAN'
        if e.kind == 'unary':
            if e.op == 'NOT':
                if left not in ('BOOLEAN','NULL'): fail('NOT requiere BOOLEAN', e)
                return 'BOOLEAN'
            if left not in NUMERIC | {'NULL'}: fail('Operador numérico con tipo incompatible', e)
            return left
        right = self.expression(e.right,scopes,aggregates)
        if e.op in ('AND','OR'):
            if left not in ('BOOLEAN','NULL') or right not in ('BOOLEAN','NULL'): fail('AND/OR requiere BOOLEAN', e)
            return 'BOOLEAN'
        if e.op in ('=','!=','<>','<','<=','>','>='):
            if not compatible(left,right): fail(f'Tipos incompatibles: {left} y {right}', e)
            return 'BOOLEAN'
        if left not in NUMERIC | {'NULL'} or right not in NUMERIC | {'NULL'}: fail('Aritmética requiere números', e)
        return 'FLOAT' if 'FLOAT' in (left,right) or e.op == '/' else 'INT'

    def condition(self, e, scopes, aggregates=False):
        if e and self.expression(e,scopes,aggregates) not in ('BOOLEAN','NULL'): fail('La condición requiere BOOLEAN', e)

    def select(self, stmt, outer=None):
        scope = {}
        scopes = [scope] + (outer or [])
        for ref, on in [(stmt.table,None)] + stmt.joins:
            if ref.alias in scope: fail(f'Alias duplicado: {ref.alias}', ref)
            scope[ref.alias] = self.table(ref.name,ref)
            if contains_query(on): fail('Las subconsultas se admiten exclusivamente en WHERE',on)
            self.condition(on,scopes)
        self.condition(stmt.where,scopes)
        for e in stmt.group_by: self.expression(e,scopes)
        for e in [i.expr for i in stmt.items] + stmt.group_by + [stmt.having] + [e for e,_ in stmt.order_by]:
            if contains_query(e): fail('Las subconsultas se admiten exclusivamente en WHERE',e)
        grouped = bool(stmt.group_by) or any(has_aggregate(i.expr) for i in stmt.items) or has_aggregate(stmt.having) or any(has_aggregate(e) for e,_ in stmt.order_by)
        def bound_signature(e):
            if e is None: return None
            if e.kind == 'column':
                alias,column = resolve(e,scopes)
                return ('column',alias,column['name'])
            return (e.kind,e.value,e.name,e.qualifier,e.op,bound_signature(e.left),bound_signature(e.right))
        group_signatures = {bound_signature(e) for e in stmt.group_by}

        def check_group(e):
            if e is None or e.kind in ('aggregate','literal','scalar','exists'): return
            if bound_signature(e) in group_signatures: return
            if e.kind == 'column':
                local = e.qualifier in scope if e.qualifier else any(c['name'] == e.name for cols in scope.values() for c in cols)
                if not local: return  # Una referencia exterior es constante para esta invocación.
                fail('Columna fuera de GROUP BY',e)
            if e.kind == 'star': fail('Columna fuera de GROUP BY', e)
            check_group(e.left)
            check_group(e.right)

        types = []
        aliases = {}
        for item in stmt.items:
            e = item.expr
            if grouped: check_group(e)
            if e.kind == 'star':
                if e.qualifier and e.qualifier not in scope: fail('Alias inexistente en comodín',e)
                types.extend(c['type'] for a,cols in scope.items() if not e.qualifier or e.qualifier == a for c in cols)
            else:
                typ = self.expression(e,scopes,True)
                types.append(typ)
                if item.alias:
                    if item.alias in aliases: fail('Alias de proyección duplicado',e)
                    aliases[item.alias] = e
        self.condition(stmt.having,scopes,True)
        if stmt.having and not grouped: fail('HAVING requiere agrupación o agregación',stmt.having)
        if grouped: check_group(stmt.having)
        for e,_ in stmt.order_by:
            resolved = aliases.get(e.name,e) if e.kind == 'column' and not e.qualifier else e
            self.expression(resolved,scopes,True)
            if grouped: check_group(resolved)
        return types

    def validate(self, stmt):
        kind = stmt.kind
        if kind == 'select':
            self.select(stmt)
            return
        if kind == 'create_table':
            if stmt.table in self.catalog['tables']: fail('Tabla duplicada',stmt)
            names = [c.name for c in stmt.columns]
            if len(set(names)) != len(names): fail('Columna duplicada',stmt)
            if sum('PRIMARY KEY' in c.constraints for c in stmt.columns) > 1: fail('Solo se admite una clave primaria simple',stmt)
            for c in stmt.columns:
                if c.type == 'VARCHAR' and c.size <= 0: fail('VARCHAR requiere longitud positiva',c)
                if len(set(c.constraints)) != len(c.constraints): fail('Restricción duplicada',c)
            self.catalog['tables'][stmt.table] = {'columns':[asdict(c) | {'location':None} for c in stmt.columns]}
            return
        if kind == 'drop_index':
            if stmt.name not in self.catalog['indexes']: fail('Índice inexistente',stmt)
            del self.catalog['indexes'][stmt.name]
            return
        columns = self.table(stmt.table,stmt)
        names = {c['name']:c for c in columns}
        scope = [{stmt.table:columns}]
        if kind == 'drop_table':
            del self.catalog['tables'][stmt.table]
            self.catalog['indexes'] = {n:i for n,i in self.catalog['indexes'].items() if i['table'] != stmt.table}
        elif kind == 'create_index':
            if stmt.name in self.catalog['indexes']: fail('Índice duplicado',stmt)
            if stmt.columns[0] not in names: fail('Columna inexistente para índice',stmt)
            self.catalog['indexes'][stmt.name] = {'table':stmt.table, 'column':stmt.columns[0]}
        elif kind == 'insert':
            selected = stmt.columns or list(names)
            if len(set(selected)) != len(selected): fail('Columna repetida en INSERT',stmt)
            for name in selected:
                if name not in names: fail(f'Columna inexistente: {name}',stmt)
            for row in stmt.rows:
                if len(row) != len(selected): fail('Cantidad de valores incorrecta en INSERT',stmt)
                for name,e in zip(selected,row):
                    if contains_query(e): fail('Las subconsultas se admiten exclusivamente en WHERE',e)
                    typ = self.expression(e,[])
                    if not assignable(names[name]['type'],typ): fail(f'Tipo incompatible en {name}',e)
                    known,value = constant_value(e)
                    if known: validate_value(value,names[name],e)
            for name,c in names.items():
                if name not in selected: validate_value(None,c,stmt)
        elif kind == 'update':
            assigned = [name for name,_ in stmt.assignments]
            if len(set(assigned)) != len(assigned): fail('Asignación duplicada',stmt)
            for name,e in stmt.assignments:
                if contains_query(e): fail('Las subconsultas se admiten exclusivamente en WHERE',e)
                if name not in names: fail(f'Columna inexistente: {name}',stmt)
                if not assignable(names[name]['type'],self.expression(e,scope)): fail(f'Tipo incompatible en {name}',e)
                known,value = constant_value(e)
                if known: validate_value(value,names[name],e)
            self.condition(stmt.where,scope)
        elif kind == 'delete':
            self.condition(stmt.where,scope)

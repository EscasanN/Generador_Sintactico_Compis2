"""Dependencias de subconsultas para reutilización segura por sentencia."""
from dataclasses import fields, is_dataclass
from .ast import Expr


def expressions(node):
    if isinstance(node, Expr):
        yield node
    if is_dataclass(node):
        for field in fields(node):
            if field.name != 'location':
                yield from expressions(getattr(node, field.name))
    elif isinstance(node, (list, tuple)):
        for child in node:
            yield from expressions(child)


def correlated(query, catalog):
    def check_query(stmt, scopes):
        refs = [stmt.table] + [ref for ref, _ in stmt.joins]
        local = {ref.alias: {c['name'] for c in catalog['tables'][ref.name]['columns']} for ref in refs}
        scopes = [local] + scopes
        def check(e):
            if e is None:
                return False
            if e.kind == 'column':
                for scope in scopes:
                    if e.qualifier:
                        if e.qualifier in scope:
                            return e.name not in scope[e.qualifier]
                    elif any(e.name in cols for cols in scope.values()):
                        return False
                return True
            return (check(e.left) or check(e.right) or
                    (e.query is not None and check_query(e.query, scopes)))
        roots = [i.expr for i in stmt.items] + [stmt.where, stmt.having] + stmt.group_by
        aliases = {i.alias: i.expr for i in stmt.items if i.alias}
        orders = [aliases.get(e.name, e) if e.kind == 'column' and not e.qualifier else e
                  for e, _ in stmt.order_by]
        roots += [on for _, on in stmt.joins] + orders
        return any(check(e) for e in roots)
    return check_query(query, [])

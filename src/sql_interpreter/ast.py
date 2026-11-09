"""AST SQL explícito, independiente de las reglas y del runtime ANTLR."""
from dataclasses import dataclass, field
from .models import SourceLocation, SqlError, bounded_integer
from .frontend import location


@dataclass
class Expr:
    kind: str
    location: SourceLocation
    value: object = None
    name: str | None = None
    qualifier: str | None = None
    op: str | None = None
    left: 'Expr | None' = None
    right: 'Expr | None' = None
    query: 'Select | None' = None


@dataclass
class ColumnDef:
    name: str
    type: str
    size: int | None
    constraints: tuple[str, ...]
    location: SourceLocation


@dataclass
class TableRef:
    name: str
    alias: str
    location: SourceLocation


@dataclass
class SelectItem:
    expr: Expr
    alias: str | None = None


@dataclass
class Select:
    location: SourceLocation
    items: list[SelectItem]
    table: TableRef
    joins: list[tuple[TableRef, Expr]]
    where: Expr | None
    group_by: list[Expr]
    having: Expr | None
    order_by: list[tuple[Expr, bool]]
    kind: str = field(default='select', init=False)


@dataclass
class ForeignKey:
    column: str
    referenced_table: str
    referenced_column: str
    location: SourceLocation


@dataclass
class Command:
    kind: str
    location: SourceLocation
    table: str = ''
    name: str = ''
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    assignments: list = field(default_factory=list)
    where: Expr | None = None
    foreign_keys: list[ForeignKey] = field(default_factory=list)


@dataclass
class Script:
    statements: list[Command | Select]


def build_ast(result) -> Script:
    if not result.accepted:
        raise SqlError('No se puede construir AST de SQL inválido', stage='PARSER')
    path = result.tokens[0].location.source_path if result.tokens else None

    def loc(ctx):
        return location(ctx.start, path)

    def expr(ctx):
        rule = type(ctx).__name__
        at = loc(ctx)
        if rule in ('ExprContext',):
            return expr(ctx.getChild(0))
        if rule in ('OrExprContext', 'AndExprContext', 'AdditiveContext', 'MultiplicativeContext'):
            node = expr(ctx.getChild(0))
            for i in range(1, ctx.getChildCount(), 2):
                node = Expr('binary', at, op=ctx.getChild(i).getText().upper(), left=node, right=expr(ctx.getChild(i+1)))
            return node
        if rule in ('NotExprContext', 'UnaryContext'):
            if ctx.getChildCount() == 1:
                return expr(ctx.getChild(0))
            return Expr('unary', at, op=ctx.getChild(0).getText().upper(), left=expr(ctx.getChild(1)))
        if rule == 'PredicateContext':
            if ctx.EXISTS():
                return Expr('exists', at, query=select(ctx.selectStmt()))
            left = expr(ctx.additive(0))
            if ctx.comparison():
                return Expr('binary', at, op=ctx.comparison().getText(), left=left, right=expr(ctx.additive(1)))
            if ctx.IN():
                return Expr('in', at, op='NOT IN' if ctx.NOT() else 'IN', left=left, query=select(ctx.selectStmt()))
            if ctx.IS():
                return Expr('is_null', at, op='IS NOT NULL' if ctx.NOT() else 'IS NULL', left=left)
            return left
        if rule == 'PrimaryContext':
            if ctx.selectStmt():
                return Expr('scalar', at, query=select(ctx.selectStmt()))
            return expr(ctx.expr() or ctx.getChild(0))
        if rule == 'ColumnRefContext':
            ids = [t.getText().lower() for t in ctx.ID()]
            return Expr('column', at, name=ids[-1], qualifier=ids[0] if len(ids) == 2 else None)
        if rule == 'AggregateContext':
            return Expr('aggregate', at, name=ctx.getChild(0).getText().upper(), left=expr(ctx.expr()) if ctx.expr() else Expr('star', at))
        if rule == 'LiteralContext':
            text = ctx.getText()
            if ctx.DATE():
                return Expr('literal', at, value=ctx.STRING().getText()[1:-1].replace("''", "'"), name='DATE')
            if ctx.STRING():
                return Expr('literal', at, value=text[1:-1].replace("''", "'"), name='VARCHAR')
            if ctx.NULL():
                return Expr('literal', at, name='NULL')
            if ctx.TRUE() or ctx.FALSE():
                return Expr('literal', at, value=bool(ctx.TRUE()), name='BOOLEAN')
            try:
                value = float(text) if ctx.DECIMAL() else bounded_integer(text,at)
            except (ValueError,OverflowError) as exc:
                raise SqlError('Literal numérico fuera de los límites del intérprete',at) from exc
            return Expr('literal', at, value=value, name='FLOAT' if ctx.DECIMAL() else 'INT')
        raise ValueError(f'Regla de expresión no soportada: {rule}')

    def table(ctx):
        ids = [t.getText().lower() for t in ctx.ID()]
        return TableRef(ids[0], ids[-1], loc(ctx))

    def reference(column, ctx):
        return ForeignKey(column, ctx.ID(0).getText().lower(), ctx.ID(1).getText().lower(), loc(ctx))

    def select(ctx):
        items = []
        for item in ctx.selectItem():
            if item.expr():
                items.append(SelectItem(expr(item.expr()), item.ID().getText().lower() if item.ID() else None))
            else:
                items.append(SelectItem(Expr('star', loc(item), qualifier=item.ID().getText().lower() if item.ID() else None)))
        where = having = None
        groups = []
        section = None
        for child in ctx.children:
            if child.getText().upper() in ('WHERE', 'GROUP', 'HAVING', 'ORDER'):
                section = child.getText().upper()
            if type(child).__name__ == 'ExprContext':
                if section == 'WHERE': where = expr(child)
                elif section == 'HAVING': having = expr(child)
                elif section == 'GROUP': groups.append(expr(child))
        return Select(loc(ctx), items, table(ctx.tableRef()), [(table(j.tableRef()), expr(j.expr())) for j in ctx.joinClause()], where, groups, having, [(expr(o.expr()), bool(o.DESC())) for o in ctx.orderItem()])

    statements = []
    for wrapper in result.native_tree.statement():
        ctx = wrapper.getChild(0)
        rule = type(ctx).__name__
        if rule == 'SelectStmtContext':
            statements.append(select(ctx))
            continue
        kind = {'CreateTableContext':'create_table', 'DropTableContext':'drop_table', 'CreateIndexContext':'create_index', 'DropIndexContext':'drop_index', 'InsertStmtContext':'insert', 'UpdateStmtContext':'update', 'DeleteStmtContext':'delete', 'AlterTableContext':'add_foreign_key'}[rule]
        command = Command(kind, loc(ctx))
        ids = ctx.ID()
        ids = ids if isinstance(ids, list) else [ids]
        names = [t.getText().lower() for t in ids]
        if kind == 'create_table':
            command.table = names[0]
            for element in ctx.tableElement():
                col = element.columnDef()
                if col is None:
                    fk = element.foreignKey()
                    command.foreign_keys.append(reference(fk.ID().getText().lower(), fk.referenceClause()))
                    continue
                typ = col.dataType()
                name = col.ID().getText().lower()
                constraints = tuple(c.getText().upper().replace('NOTNULL','NOT NULL').replace('PRIMARYKEY','PRIMARY KEY')
                                    for c in col.constraint() if c.referenceClause() is None)
                command.columns.append(ColumnDef(name, typ.getChild(0).getText().upper(), bounded_integer(typ.INTEGER().getText(),loc(col)) if typ.INTEGER() else None, constraints, loc(col)))
                for constraint in col.constraint():
                    if constraint.referenceClause():
                        command.foreign_keys.append(reference(name, constraint.referenceClause()))
        elif kind == 'add_foreign_key':
            command.table = names[0]
            fk = ctx.foreignKey()
            command.foreign_keys.append(reference(fk.ID().getText().lower(), fk.referenceClause()))
        elif kind in ('drop_table', 'delete', 'update', 'insert'):
            command.table = names[0]
            if kind == 'insert':
                command.columns = names[1:]
                command.rows = [[expr(e) for e in row.expr()] for row in ctx.valueRow()]
            if kind == 'update':
                command.assignments = [(a.ID().getText().lower(), expr(a.expr())) for a in ctx.assignment()]
            if kind in ('update', 'delete'):
                command.where = expr(ctx.expr()) if ctx.expr() else None
        elif kind == 'create_index':
            command.name, command.table, column = names
            command.columns = [column]
        else:
            command.name = names[0]
        statements.append(command)
    return Script(statements)

# Generated from SQL.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .SQLParser import SQLParser
else:
    from SQLParser import SQLParser

# This class defines a complete generic visitor for a parse tree produced by SQLParser.

class SQLVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by SQLParser#script.
    def visitScript(self, ctx:SQLParser.ScriptContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#statement.
    def visitStatement(self, ctx:SQLParser.StatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#createTable.
    def visitCreateTable(self, ctx:SQLParser.CreateTableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#columnDef.
    def visitColumnDef(self, ctx:SQLParser.ColumnDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#dataType.
    def visitDataType(self, ctx:SQLParser.DataTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#constraint.
    def visitConstraint(self, ctx:SQLParser.ConstraintContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#dropTable.
    def visitDropTable(self, ctx:SQLParser.DropTableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#createIndex.
    def visitCreateIndex(self, ctx:SQLParser.CreateIndexContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#dropIndex.
    def visitDropIndex(self, ctx:SQLParser.DropIndexContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#insertStmt.
    def visitInsertStmt(self, ctx:SQLParser.InsertStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#valueRow.
    def visitValueRow(self, ctx:SQLParser.ValueRowContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#updateStmt.
    def visitUpdateStmt(self, ctx:SQLParser.UpdateStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#assignment.
    def visitAssignment(self, ctx:SQLParser.AssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#deleteStmt.
    def visitDeleteStmt(self, ctx:SQLParser.DeleteStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#selectStmt.
    def visitSelectStmt(self, ctx:SQLParser.SelectStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#selectItem.
    def visitSelectItem(self, ctx:SQLParser.SelectItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#tableRef.
    def visitTableRef(self, ctx:SQLParser.TableRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#joinClause.
    def visitJoinClause(self, ctx:SQLParser.JoinClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#orderItem.
    def visitOrderItem(self, ctx:SQLParser.OrderItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#expr.
    def visitExpr(self, ctx:SQLParser.ExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#orExpr.
    def visitOrExpr(self, ctx:SQLParser.OrExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#andExpr.
    def visitAndExpr(self, ctx:SQLParser.AndExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#notExpr.
    def visitNotExpr(self, ctx:SQLParser.NotExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#predicate.
    def visitPredicate(self, ctx:SQLParser.PredicateContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#comparison.
    def visitComparison(self, ctx:SQLParser.ComparisonContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#additive.
    def visitAdditive(self, ctx:SQLParser.AdditiveContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#multiplicative.
    def visitMultiplicative(self, ctx:SQLParser.MultiplicativeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#unary.
    def visitUnary(self, ctx:SQLParser.UnaryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#primary.
    def visitPrimary(self, ctx:SQLParser.PrimaryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#columnRef.
    def visitColumnRef(self, ctx:SQLParser.ColumnRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#aggregate.
    def visitAggregate(self, ctx:SQLParser.AggregateContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SQLParser#literal.
    def visitLiteral(self, ctx:SQLParser.LiteralContext):
        return self.visitChildren(ctx)



del SQLParser
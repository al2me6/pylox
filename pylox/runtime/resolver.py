from collections import abc
from contextlib import contextmanager, nullcontext
from typing import Any, Iterator, List, Optional, Set

from pylox.language.lox_types import LoxIdentifier
from pylox.lexing.token import Token
from pylox.parsing.expr import *
from pylox.parsing.stmt import *
from pylox.runtime.stacked_map import StackedMap
from pylox.utilities.error import LoxSyntaxError
from pylox.utilities.visitor import Visitor


class Resolver(Visitor):
    def __init__(self) -> None:
        self._resolved_vars: StackedMap[str, LoxIdentifier] = StackedMap()
        self._dirty: Set[str] = set()

    def resolve(self, ast: List[Stmt]) -> None:
        self._resolved_vars.clear()
        for stmt in ast:
            self.visit(stmt)

    def visit(self, visitable: Any, *args: Any, **kwargs: Any) -> None:
        # Blanket impl.
        if isinstance(visitable, (Expr, Stmt)) and not isinstance(visitable, (
                AssignmentExpr,
                VariableExpr,
                FunctionStmt,
                StmtGroup,
                VarStmt,
        )):
            for attr in vars(visitable).values():
                for sub_attr in attr if isinstance(attr, abc.Iterable) else (attr, ):
                    if isinstance(sub_attr, (Expr, Stmt)):
                        self.visit(sub_attr)
        else:
            super().visit(visitable)

    def _register_ident(self, ident: Token) -> LoxIdentifier:
        if self._resolved_vars.is_local() and ident.lexeme in self._resolved_vars[-1]:
            raise LoxSyntaxError.at_token(ident, "Variable with this name already declared in this scope.", fatal=True)
        uniq_id = LoxIdentifier(id(ident) ^ id(self))
        self._resolved_vars.define(ident.lexeme, uniq_id)
        return uniq_id

    def _resolve_ident(self, ident: Token) -> Optional[LoxIdentifier]:
        # TODO: Support out-or-order declarations, presumably by resolving all statements
        # in a statement group before recursing.
        try:
            if ident.lexeme in self._dirty:
                raise LoxSyntaxError.at_token(ident, "Cannot read local variable in its own initializer.", fatal=True)
            return self._resolved_vars.get(ident.lexeme)
        except KeyError:  # "Variable not found" errors are deferred to runtime.
            return None

    @contextmanager
    def _mark_as_dirty(self, ident: Token) -> Iterator[None]:
        self._dirty.add(ident.lexeme)
        try:
            yield
        finally:
            self._dirty.discard(ident.lexeme)

    def _visit_AssignmentExpr__(self, expr: AssignmentExpr) -> None:
        expr.target_id = self._resolve_ident(expr.name)
        self.visit(expr.value)

    def _visit_VariableExpr__(self, expr: VariableExpr) -> None:
        expr.target_id = self._resolve_ident(expr.name)

    def _visit_FunctionStmt__(self, stmt: FunctionStmt) -> None:
        stmt.uniq_id = self._register_ident(stmt.name)
        with self._resolved_vars.scope():
            for param in stmt.params:
                param.target_id = self._register_ident(param.name)
            self.visit(stmt.body)

    def _visit_VarStmt__(self, stmt: VarStmt) -> None:
        if stmt.initializer:
            with self._mark_as_dirty(stmt.name) if self._resolved_vars.is_local() else nullcontext():
                self.visit(stmt.initializer)
        stmt.uniq_id = self._register_ident(stmt.name)

    def _visit_StmtGroup__(self, stmt: StmtGroup) -> None:
        # Only true block statements are scoped.
        with self._resolved_vars.scope() if isinstance(stmt, BlockStmt) else nullcontext():
            for s in stmt.body:
                self.visit(s)

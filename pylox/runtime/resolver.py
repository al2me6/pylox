from collections import abc
from contextlib import nullcontext
from typing import List, Optional, Union

from pylox.language.lox_types import FunctionKind, LoxIdentifier
from pylox.lexing.token import Token
from pylox.parsing.expr import *
from pylox.parsing.stmt import *
from pylox.utilities.error import LoxSyntaxError
from pylox.utilities.scoped_state_handler import ScopedStateHandler
from pylox.utilities.stacked_map import StackedMap
from pylox.utilities.visitor import Visitor


class Resolver(Visitor[Union[Expr, Stmt], None]):
    def __init__(self) -> None:
        self._resolved_vars: StackedMap[str, LoxIdentifier] = StackedMap()
        self._partially_init_var: ScopedStateHandler[Optional[str]] = ScopedStateHandler(None)
        self._is_resolving_class: ScopedStateHandler[bool] = ScopedStateHandler(False)
        self._is_resolving_constructor: ScopedStateHandler[bool] = ScopedStateHandler(False)

    def resolve(self, ast: List[Stmt]) -> None:
        self._resolved_vars.clear()
        for stmt in ast:
            self.visit(stmt)

    def visit(self, visitable: Union[Expr, Stmt]) -> None:
        # Blanket impl.
        if isinstance(visitable, (Expr, Stmt)) and not isinstance(visitable, (
                AnonymousFunctionExpr,
                AssignmentExpr,
                VariableExpr,
                GroupingDirective,
                ClassDeclarationStmt,
                VariableDeclarationStmt,
        )):
            # Diagnostics.
            if isinstance(visitable, ThisExpr) and not self._is_resolving_class.state:
                raise LoxSyntaxError.at_token(
                    visitable.keyword, "Cannot use 'this' outside of a class.", fatal=True
                )
            if isinstance(visitable, ReturnStmt) and self._is_resolving_constructor.state:
                if visitable.expression is not None:
                    raise LoxSyntaxError.at_token(
                        visitable.keyword, "Cannot return a value from an initializer.", fatal=True
                    )

            for attr in vars(visitable).values():
                for sub_attr in attr if isinstance(attr, abc.Iterable) else (attr, ):
                    if isinstance(sub_attr, (Expr, Stmt)):
                        self.visit(sub_attr)
        else:
            super().visit(visitable)

    def _register_ident(self, ident: Token) -> LoxIdentifier:
        if self._resolved_vars.is_local() and ident.lexeme in self._resolved_vars[-1]:
            raise LoxSyntaxError.at_token(
                ident, "Variable with this name already declared in this scope.", fatal=True
            )
        uniq_id = LoxIdentifier(id(ident) ^ id(self))
        self._resolved_vars.define(ident.lexeme, uniq_id)
        return uniq_id

    def _resolve_ident(self, ident: Token) -> Optional[LoxIdentifier]:
        # TODO: Support out-or-order top level declarations, presumably by resolving
        # all top-level names before recursing.
        try:
            if ident.lexeme == self._partially_init_var.state:
                raise LoxSyntaxError.at_token(
                    ident, "Cannot read local variable in its own initializer.", fatal=True
                )
            return self._resolved_vars.get(ident.lexeme)
        except KeyError:  # "Variable not found" errors are deferred to runtime.
            return None

    def _visit_AnonymousFunctionExpr__(self, expr: AnonymousFunctionExpr) -> None:
        with self._resolved_vars.scope():
            for param in expr.params:
                param.target_id = self._register_ident(param.target)
            self.visit(expr.body)

    def _visit_AssignmentExpr__(self, expr: AssignmentExpr) -> None:
        expr.target_id = self._resolve_ident(expr.target)
        self.visit(expr.value)

    def _visit_VariableExpr__(self, expr: VariableExpr) -> None:
        expr.target_id = self._resolve_ident(expr.target)

    def _visit_GroupingDirective__(self, stmt: GroupingDirective) -> None:
        # Only true block statements are scoped.
        with self._resolved_vars.scope() if isinstance(stmt, BlockStmt) else nullcontext():
            for item in stmt.body:
                self.visit(item)

    def _visit_ClassDeclarationStmt__(self, stmt: ClassDeclarationStmt) -> None:
        stmt.uniq_id = self._register_ident(stmt.name)
        with self._resolved_vars.scope(), self._is_resolving_class.enter(True):
            for item in stmt.instance_variables:
                self.visit(item)

    def _visit_VariableDeclarationStmt__(self, stmt: VariableDeclarationStmt) -> None:
        # HACK: special-case function declarations by registering the name before
        # resolving the body to allow recursion.
        if isinstance(stmt.initializer, AnonymousFunctionExpr):
            stmt.uniq_id = self._register_ident(stmt.ident)
            # Methods with name `init` are constructors.
            if stmt.initializer.kind is FunctionKind.METHOD and stmt.ident.lexeme == "init":
                stmt.initializer.kind = FunctionKind.CONSTRUCTOR
            with self._is_resolving_constructor.enter(stmt.initializer.kind is FunctionKind.CONSTRUCTOR):
                self.visit(stmt.initializer)
        else:
            if stmt.initializer:
                # "Poison" the identifier of a local assignment expression when parsing the RHS.
                # As in, disallow statements of the form `{ var a = a; }`.
                with (self._partially_init_var.enter(stmt.ident.lexeme) if self._resolved_vars.is_local()
                      else nullcontext()):
                    self.visit(stmt.initializer)
            stmt.uniq_id = self._register_ident(stmt.ident)

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ("app", "actions", "autonomy", "backup", "compute", "connection", "permissions", "senses", "settings",
            "updates", "voice", "ui", "i18n")


def _walk_eager(node):
    stack = [node]
    while stack:
        current = stack.pop()
        for child in ast.iter_child_nodes(current):
            if isinstance(child, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            stack.append(child)
            yield child


def _ordered(statements):
    for statement in statements:
        nodes = [statement, *_walk_eager(statement)]
        nodes.sort(key=lambda n: (getattr(n, "lineno", 0), getattr(n, "col_offset", 0)))
        yield from nodes


def _self_attr(node):
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
        return node.attr
    return None


class _Checker:
    def __init__(self, cls):
        self.methods = {n.name: n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.statics = set(self.methods)
        for n in cls.body:
            if isinstance(n, ast.Assign):
                self.statics.update(t.id for t in n.targets if isinstance(t, ast.Name))
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                self.statics.add(n.target.id)
        self.assigned: set[str] = set()
        self.problems: list[str] = []
        self.visiting: set[str] = set()

    def run(self):
        self.visit(self.methods["__init__"])
        return self.problems

    def visit(self, function):
        if function.name in self.visiting:
            return
        self.visiting.add(function.name)
        for statement in function.body:
            self.statement(statement, function.name)
        self.visiting.discard(function.name)

    def statement(self, statement, owner):
        targets = []
        if isinstance(statement, ast.Assign):
            targets = statement.targets
        elif isinstance(statement, (ast.AnnAssign, ast.AugAssign)):
            targets = [statement.target]
        if isinstance(statement, (ast.Assign, ast.AnnAssign)) and statement.value is not None:
            self.expression(statement.value, owner)
        elif isinstance(statement, ast.AugAssign):
            self.expression(statement.value, owner)
        elif isinstance(statement, ast.Expr):
            self.expression(statement.value, owner)
        elif isinstance(statement, (ast.If, ast.While)):
            self.expression(statement.test, owner)
            for inner in [*statement.body, *statement.orelse]:
                self.statement(inner, owner)
        elif isinstance(statement, (ast.For, ast.AsyncFor)):
            self.expression(statement.iter, owner)
            for inner in [*statement.body, *statement.orelse]:
                self.statement(inner, owner)
        elif isinstance(statement, (ast.With, ast.AsyncWith)):
            for item in statement.items:
                self.expression(item.context_expr, owner)
            for inner in statement.body:
                self.statement(inner, owner)
        elif isinstance(statement, ast.Try):
            for inner in [*statement.body, *statement.orelse, *statement.finalbody]:
                self.statement(inner, owner)
            for handler in statement.handlers:
                for inner in handler.body:
                    self.statement(inner, owner)
        elif isinstance(statement, ast.Return) and statement.value is not None:
            self.expression(statement.value, owner)
        for target in targets:
            for sub in ast.walk(target):
                name = _self_attr(sub)
                if name and isinstance(sub.ctx, ast.Store):
                    self.assigned.add(name)

    def expression(self, expression, owner):
        for node in _ordered([expression]):
            name = _self_attr(node)
            if name is None or not isinstance(node.ctx, ast.Load):
                continue
            if name not in self.statics and name not in self.assigned:
                self.problems.append(f"{owner}:{node.lineno} self.{name}")
            if isinstance(node.ctx, ast.Load) and name in self.methods and self._called(expression, node):
                self.visit(self.methods[name])

    def _called(self, expression, attribute):
        for node in [expression, *_walk_eager(expression)]:
            if isinstance(node, ast.Call) and node.func is attribute:
                return True
        return False


def _classes():
    for package in PACKAGES:
        for path in sorted((ROOT / package).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and not node.bases and any(
                        isinstance(n, ast.FunctionDef) and n.name == "__init__" for n in node.body):
                    yield path, node


class InitOrderTest(unittest.TestCase):
    def test_no_attribute_is_read_before_it_is_assigned(self):
        failures = []
        for path, cls in _classes():
            for problem in _Checker(cls).run():
                failures.append(f"{path.relative_to(ROOT)}::{cls.name}.{problem}")
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()

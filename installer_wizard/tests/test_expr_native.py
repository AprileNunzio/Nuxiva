import math
import unittest
from unittest import mock

import native_core

from features.automations import expr
from features.automations.expr import ExprError, functions, wrap

NATIVE = native_core.symbol("expr_evaluate") is not None


class States:
    def __init__(self):
        self.calls = []

    def state(self, eid, default=""):
        self.calls.append(eid)
        return {"sensor.temp": "21,5", "light.salotto": "on", "sensor.count": "3"}.get(eid, default)

    def attr(self, eid, name, default=""):
        return {"brightness": 128, "friendly_name": "Luce Salotto"}.get(name, default)

    def since(self, eid):
        return 42.0

    def present(self, who=""):
        return who.lower() in ("", "nunzio")

    def people(self):
        return ["Nunzio", "Giulia"]

    def quiet(self):
        return False


def names(states):
    base = functions(states)
    base.update({"x": 5, "y": "a", "f": 2.5, "flag": True, "nothing": None, "items": [3, 1, 2], "empty": [],
                 "trigger": wrap({"to": "on", "from": "off", "data": {"level": 7, "who": "Nunzio"}}),
                 "vars": wrap({"count": 3, "names": ["a", "b"]}), "big": 2 ** 70, "neg": -7})
    return base


CORPUS = [
    "2 + 3 * 4", "7 // 2", "7 // -2", "-7 // 2", "7 % -3", "-7 % 3", "7.5 % 2", "-7.5 // 2", "7.5 // -2", "7 / 2",
    "2 ** 10", "2 ** 1000", "2 ** -2", "2.5 ** 2", "(-2) ** 3", "0 ** 0", "10 ** 64", "x ** 0.5",
    "True + True", "flag * 3", "'a' + 1", "1 + 'a'", "'a' + 'b'", "'3' * 2", "'3' - '1'", "x - '2,5'", "items * 2",
    "[1] * 0", "[1] * -1", "nothing + 1", "y * 2", "f + x", "-x", "+flag", "-f", "not x", "not empty",
    "x > 3 and y == 'a'", "x > 3 and 0", "0 or '' or 'z'", "'' or nothing", "x and y and f",
    "'sì' if x else 'no'", "1 if empty else 2", "1 < x < 10", "1 < x > 10", "'26' > 25", "'a' < 'b'",
    "'10' < '9'", "1 == 1.0", "1 == True", "'1' == 1", "items == [3, 1, 2]", "nothing == None", "x != 5",
    "x is None", "x is not None", "'a' in 'casa'", "2 in items", "'k' not in {'j': 1}", "'j' in {'j': 1}",
    "1 in {1.0: 'a'}", "trigger.to", "trigger.data.level + 1", "trigger.missing", "trigger['to']",
    "trigger['data']['who']", "items[0]", "items[-1]", "items[9]", "items['a']", "y[0]", "'casa'[-1]",
    "vars.names[1]", "{'a': 1}['a']", "{'a': 1}['b']", "{1: 'x', True: 'y'}", "[1, 'a', None, True, 2.5]",
    "(1, 2)", "()", "[]", "{}", "1, 2", "big", "big + 1", "big > 10 ** 20", "neg % 5", "abs(neg)", "abs(-2.5)",
    "state('sensor.temp')", "num(state('sensor.temp')) + 1", "float('3,25')", "num('x')", "num('x', 9)",
    "int('7,9')", "int(-3.7)", "int(True)", "str(1.0)", "str(1e16)", "str(1.5e-05)", "str(0.1 + 0.2)",
    "str([1, 'a', None])", "str({'a': [1.5]})", "str(nothing)", "str(flag)", "str()", "bool('')", "bool(items)",
    "len('città')", "len(items)", "len({})", "round(2.675, 2)", "round(2.5)", "round(3.5)", "round('2,5')",
    "round(1234.5, -2)", "round(f, 1)", "min(items)", "max(items)", "min(4, 2, 9)", "max('ab', 'b')",
    "min([2.5, 1])", "max('casa')", "sum(items)", "sum([1.5, 2])", "sum([])", "lower('ÀB')", "upper('città')",
    "sqrt(16)", "sqrt('2,25')", "contains('Salotto', 'LOT')", "contains(items, 3)", "join(items)",
    "join(['a', 'b'], '-')", "join('abc', '')", "attr('light.salotto', 'brightness') > 100",
    "is_state('light.salotto', 'on', 'off')", "is_state('light.salotto', 'off')", "since('x') > 10",
    "present('Nunzio')", "present('Ospite')", "'Giulia' in people()", "quiet()", "true and vero",
    "falso or none", "null", "mai_impostata", "mai_impostata == None", "0x1F + 0b11 + 0o7 + 1_000",
    "'a\\tb' 'c'", "r'a\\n'", "'\\u00e8'", "\"doppie\"", "'''tripla'''", "1e3", ".5", "5.", "1_000.5",
    "1 / 0", "1 // 0", "1 % 0", "1.0 / 0", "0 ** -1", "sqrt(-1)", "int('nan')", "len(5)", "min([])",
    "ignota(1)", "x.y", "x.__class__", "__import__('os')", "(lambda: 1)()", "[i for i in items]",
    "open('f')", "items[1:2]", "{1, 2}", "~x", "x | 1", "x << 1", "f'{x}'", "b'x'", "1j", "x = 1",
    "x := 1", "", "   ", "(", "1 +", "'aperta", "@", "x if y", "trigger.to.upper()", "False and x.y()",
    "abs('x')", "sum(['a'])", "join(items, 1)", "'x' in 5", "[1] in {'a': 1}", "{[1]: 2}", "1 < 'a'",
    "(-8) ** (1/3)", "items + 1", "items - [1]", "-y", "1e308 * 10", "2.0 ** 1024", "round(1e300, 2)",
]


def run(fn, source, states):
    try:
        return "ok", fn(source, names(states))
    except (ExprError, TypeError, ValueError, OverflowError, ZeroDivisionError, KeyError, AttributeError,
            MemoryError, RecursionError) as exc:
        return "err", type(exc).__name__


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, float):
        return (math.isnan(a) and math.isnan(b)) or a == b
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    return a == b


KNOWN_STRICTER = {"(-8) ** (1/3)", "1e308 * 10", "2.0 ** 1024", "1 < x > 10", "b'x'", "1j"}
HUGE_INTS = {"10 ** 64"}


@unittest.skipUnless(NATIVE, "modulo nativo assente")
class ExprParityTest(unittest.TestCase):

    def test_rust_matches_python_on_the_corpus(self):
        mismatches = []
        for source in CORPUS:
            rust = run(expr.evaluate, source, States())
            py = run(expr._py_evaluate, source, States())
            if rust[0] == "err" and py[0] == "err":
                continue
            if rust[0] == py[0] == "ok" and same(rust[1], py[1]):
                continue
            if source in KNOWN_STRICTER and rust[0] == "err":
                continue
            if source in HUGE_INTS and rust[0] == py[0] == "ok" and rust[1] == float(py[1]):
                continue
            mismatches.append((source, rust, py))
        self.assertEqual(mismatches, [])

    def test_errors_become_expr_error(self):
        for source in ("1 / 0", "x.__class__", "ignota()", "items[1:2]", "1 +"):
            with self.subTest(source=source), self.assertRaises(ExprError):
                expr.evaluate(source, names(States()))

    def test_host_functions_are_called_lazily(self):
        states = States()
        expr.evaluate("False and state('a') or state('b')", names(states))
        self.assertEqual(states.calls, ["b"])

    def test_host_exceptions_propagate(self):
        def boom(_):
            raise KeyError("rotto")
        with self.assertRaises(KeyError):
            expr.evaluate("boom(1)", {"boom": boom})

    def test_resource_limits(self):
        for source in ("[0] * 100000", "'x' * 9", "1 + " * 99 + "1", "(" * 150 + "1" + ")" * 150, "[" * 120,
                       "str(items) " + "+ str(items) " * 30):
            with self.subTest(source=source[:20]):
                try:
                    expr.evaluate(source, names(States()))
                except ExprError:
                    pass
        with self.assertRaises(ExprError):
            expr.evaluate("[0] * 100000", {})
        with self.assertRaises(ExprError):
            nested = 1
            for _ in range(40):
                nested = [nested]
            expr.evaluate("x", {"x": nested})
        self.assertEqual(expr.render("Ci sono {{ t }} gradi", {"t": 28.0}), "Ci sono 28 gradi")
        self.assertEqual(expr.render("{{ 1 / 0 }}!", {}), "[divisione per zero]!")


class ExprFallbackTest(unittest.TestCase):

    def test_python_fallback(self):
        with mock.patch.object(native_core, "symbol", return_value=None):
            self.assertEqual(expr.evaluate("2 + 3", {}), 5)
            with self.assertRaises(ExprError):
                expr.evaluate("open('f')", {})


if __name__ == "__main__":
    unittest.main()

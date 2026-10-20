"""A function that returns a function, a nested function, a helper (doc 04 section 19.8). returns_function.py:
f(x) returning lambda y: E is lowered as the function f(x, y); behaviour_v04.py: a nested function takes the
variables it reads from its enclosing function as parameters, and the v0.4 interpreter runs what interp.pl threw
on; eval_ta.helper_functions: a function called by one that computes something else is that function's step."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import crosslang_frontends
import learn_facts

crosslang_frontends.install(lisp_sbcl=False)
import behaviour_v04
import eval_ta
import io_trace


def facts(source: str) -> str:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'p.py'
        path.write_text(source, encoding='utf-8')
        return learn_facts.tree_facts(path)[1]


def runs(source: str) -> dict[str, list]:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'p.py'
        path.write_text(source, encoding='utf-8')
        return {n: [r[1] for r in d['runs']] for n, d in io_trace.run_functions(path).items()}


CURRIED = ('def lcm(x):\n    return lambda y: 0 if 0 in (x, y) else abs(y * (x // gcd_(x)(y)))\n\n'
           'def gcd_(x):\n    def go(a, b):\n        return go(b, a % b) if 0 != b else a\n'
           '    return lambda y: go(abs(x), abs(y))\n')


class ReturnsFunctionTests(unittest.TestCase):
    def test_a_returned_lambda_adds_its_parameters(self):
        params = [line for line in facts(CURRIED).splitlines() if line.startswith('param(')]
        self.assertIn("param('f1',1,'y').", params)

    def test_two_levels(self):
        out = facts('def f(a):\n    return lambda b: lambda c: a + b + c\n')
        self.assertIn("param('f1',2,'c').", out)

    def test_a_function_returning_a_value_is_unchanged(self):
        out = facts('def f(a):\n    g = lambda b: b + 1\n    return g(a)\n')
        self.assertNotIn("param('f1',1,", out)

    def test_curried_lcm_runs_as_lcm(self):
        self.assertEqual(runs(CURRIED)['lcm'][:5], ['36', '35', '0', '42', '300'])


class NestedFunctionTests(unittest.TestCase):
    def test_free_variables_become_parameters(self):
        funs = [('f', ['x'], ('seq', [('assign', ('var', 's'), ('var', 'x')),
                                      ('return', ('call', 'reduce', [('var', 'go'), ('var', 'x'), ('int', 0)]))])),
                ('f.go', ['a', 'b'], ('seq', [('return', ('op', 'add', [('var', 'a'), ('var', 's')]))]))]
        out = dict((n, (p, b)) for n, p, b in behaviour_v04.lift(funs))
        self.assertEqual(out['f.go'][0], ['a', 'b', 's'])
        self.assertIn("('lambda', ['a', 'b'], ('call', 'f.go'", repr(out['f'][1]))

    def test_levenshtein_written_with_reduce_and_scanl(self):
        src = ('from functools import reduce\nfrom itertools import accumulate, chain\n'
               'def levenshtein(sa):\n    s1 = list(sa)\n    def go(ns, c):\n        n, ns1 = ns[0], ns[1:]\n'
               '        def gap(z, c1xy):\n            c1, x, y = c1xy\n'
               '            return min(y + 1, z + 1, x + 1 if c != c1 else x)\n'
               '        return scanl(gap)(n + 1)(zip(s1, ns, ns1))\n'
               '    return lambda sb: reduce(go, list(sb), list(range(len(s1) + 1)))[-1]\n'
               'def scanl(f):\n    return lambda a: lambda xs: list(accumulate(chain([a], xs), f))\n')
        self.assertEqual(runs(src)['levenshtein'][:5], ['3', '1', '2', '2', '0'])

    def test_a_boolean_in_arithmetic_is_0_or_1(self):
        self.assertEqual(runs('def f(a, b):\n    return a + (a != b)\n')['f'][:2], ['13', '8'])


class HelperTests(unittest.TestCase):
    def test_a_callee_computing_something_else_is_a_helper(self):
        per_fn = {'funcs': ['lcm', 'gcd_', 'gcd_.go', 'main'], 'normal': [], 'hand': [('gcd_.go', 'greatest_common_divisor')],
                  'calls': [('lcm', 'gcd_'), ('gcd_', 'go'), ('main', 'lcm')]}
        by_fn = {'lcm': {'least_common_multiple'}, 'gcd_': {'greatest_common_divisor'},
                 'gcd_.go': {'greatest_common_divisor'}}
        labels = {'least_common_multiple', 'greatest_common_divisor'}
        gs = {lab: lab for lab in labels}
        self.assertEqual(eval_ta.helper_functions(per_fn, by_fn, labels, gs), {'gcd_', 'gcd_.go'})

    def test_a_callee_computing_the_same_is_not(self):
        per_fn = {'funcs': ['sort', 'sort.merge'], 'normal': [], 'hand': [], 'calls': [('sort', 'merge')]}
        by_fn = {'sort': {'merge_sort'}, 'sort.merge': {'merge_sort'}}
        gs = {'merge_sort': 'merge_sort'}
        self.assertEqual(eval_ta.helper_functions(per_fn, by_fn, {'merge_sort'}, gs), set())


if __name__ == '__main__':
    unittest.main()

"""Conversion fixes (doc 04 section 19). 19.1 prolog/trace_returns.pl: a returned value is traced through the variable holding a recursive
call's result, the same as when the call is written in the return; a variable used elsewhere is not traced. 19.2
haskell_logic.py: a Haskell recursion ends at its base cases (the loop condition from a pattern base case)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import learn_facts


def nodes(source: str) -> dict[str, set[str]]:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'p.py'
        path.write_text(source, encoding='utf-8')
        kind, text = learn_facts.tree_facts(path)
        out = {}
        for line in learn_facts.swipl_facts('tree_main', learn_facts.TREE_MAIN, kind, text):
            if line.startswith('NODE|'):
                _, fn, node = line.split('|', 2)
                out.setdefault(fn, set()).add(node)
        return out


DIRECT = 'def f(n):\n    if n > 1:\n        return n * f(n - 1)\n    return 1\n'
THROUGH = 'def f(n):\n    z = 1\n    if n > 1:\n        z = n * f(n - 1)\n    return z\n'
USED = ('def h(t):\n    if t is None:\n        return 1\n    a = h(t.left)\n    b = h(t.right)\n'
        '    if a != b:\n        return 0\n    return a + b\n')


class TraceReturnsTests(unittest.TestCase):
    def test_through_a_variable_as_direct(self):
        self.assertEqual(nodes(THROUGH)['f'], nodes(DIRECT)['f'])
        self.assertEqual(nodes(THROUGH)['f'], {'numeric>recurrence>range_accumulation'})

    def test_a_variable_also_tested_is_not_traced(self):
        self.assertEqual(nodes(USED)['h'], {'numeric>recurrence>double_recursion'})

    def test_no_recursive_value_is_not_traced(self):
        src = 'def g(xs):\n    s = 0\n    for x in xs:\n        s = s + x\n    return s\n'
        self.assertEqual(nodes(src)['g'], {'sequence_query>aggregate>gatherer'})


class HaskellBaseCaseTests(unittest.TestCase):
    def test_pattern_base_case_ends_the_recursion(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'f.hs'
            path.write_text('fac n = go 1 n\n  where go acc 0 = acc\n        go acc n = go (acc * n) (n - 1)\n')
            kind, text = learn_facts.tree_facts(path)
            got = {line.split('|', 2)[2] for line in learn_facts.swipl_facts('tree_main', learn_facts.TREE_MAIN, kind, text)
                   if line.startswith('NODE|go|')}
        self.assertEqual(got, {'numeric>recurrence>range_accumulation'})


if __name__ == '__main__':
    unittest.main()

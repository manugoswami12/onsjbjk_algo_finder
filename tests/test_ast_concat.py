"""What Python tells about its own programs (doc 04 section 19.7). pyast_facts.py: which names hold lists, read by
Python's ast (static, never run); prolog/ast_concat.pl: `+` with a list operand is concat; families_v02.pl
partition_evidence/1: a join of recursive results is a partition sort only on parts split by a comparison;
prolog/slice_write.pl: q[:] = E in a function that returns nothing is a write of q, its output."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import learn_facts
import pyast_facts


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


def facts(source: str) -> str:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'p.py'
        path.write_text(source, encoding='utf-8')
        return pyast_facts.facts(path)


PARTITION = 'partition_recursive'
QUICK = ('def q(a):\n    if len(a) <= 1:\n        return a\n    p = a[0]\n'
         '    lo = [x for x in a[1:] if x < p]\n    hi = [x for x in a[1:] if x >= p]\n    return q(lo) + [p] + q(hi)\n')
HANOI = ('def h(n, a, b, c):\n    if n == 0:\n        return []\n'
         '    return h(n - 1, a, c, b) + [(a, c)] + h(n - 1, b, a, c)\n')


class PyAstFactsTests(unittest.TestCase):
    def test_list_names_and_functions(self):
        out = facts('def f(xs):\n    ys: list[int] = [1]\n    zs = ys + xs[1:]\n    return zs\n')
        self.assertIn("list_var('f','ys').", out)
        self.assertIn("list_var('f','zs').", out)
        self.assertIn("list_param('f','xs').", out)
        self.assertIn("list_func('f').", out)

    def test_numbers_are_not_lists(self):
        self.assertEqual(facts('def f(a, b):\n    s = a + b\n    return s\n'), '')

    def test_each_predicate_together(self):
        names = [line.split('(')[0] for line in facts('def f(x):\n    a = [x]\n    return x[1:]\n'
                                                       'def g(y):\n    b = [y]\n    return y[1:]\n').split()]
        self.assertEqual(names, sorted(names, key=['list_var', 'list_param', 'list_func'].index))

    def test_unparsable_file_gives_no_facts(self):
        self.assertEqual(facts('def f(:\n'), '')


class ListJoinTests(unittest.TestCase):
    def test_partition_by_comparison_is_a_partition_sort(self):
        self.assertTrue(any(PARTITION in n for n in nodes(QUICK)['q']))

    def test_a_join_of_two_recursive_results_alone_is_not(self):
        self.assertFalse(any(PARTITION in n for n in nodes(HANOI).get('h', set())))


class SliceWriteTests(unittest.TestCase):
    def test_in_place_rewrite_is_a_transformation(self):
        src = 'def f(seq):\n    for i in range(1, len(seq)):\n        seq[:] = seq[:i] + [seq[i]] + seq[i + 1:]\n'
        self.assertIn('sequence_transformation', nodes(src).get('f', set()))

    def test_a_function_with_a_return_is_left_as_it_is(self):    # rotate_matrix.py reverse_column keeps its node
        src = 'def f(m):\n    m[:] = [x[::-1] for x in m]\n    return m\n'
        self.assertEqual(nodes(src)['f'], {'sequence_query'})


if __name__ == '__main__':
    unittest.main()

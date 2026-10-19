"""v0.3 fixes, separate from the pipeline (doc 04 section 18.7): the tree branches of prolog/families_v03.pl (through
prolog/tree_v03.pl) and the Lisp loop's `finally` (lisp_loop_v03.py). Each positive case is a shape the v0.2 tree or
lowering got wrong; each negative case is a near shape the new branch must leave alone."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import learn_facts

DATA = ROOT / 'tests' / 'data' / 'v03'
TREE_V03 = ROOT / 'prolog' / 'tree_v03.pl'


def nodes(path: Path, tree: Path) -> set[str]:
    kind, text = learn_facts.tree_facts(path)
    return {line.split('|', 2)[2] for line in learn_facts.swipl_facts('tree_main', tree, kind, text)
            if line.startswith('NODE|')}


class TreeV03Tests(unittest.TestCase):
    def test_partition_through_variables(self):
        self.assertEqual(nodes(DATA / 'qs_vars.py', learn_facts.TREE_MAIN), {'sequence_query'})
        self.assertEqual(nodes(DATA / 'qs_vars.py', TREE_V03),
                         {'sequence_transformation>comparison_sort>partition_recursive'})

    def test_whole_slice_rewrite(self):
        self.assertEqual(nodes(DATA / 'inplace_slice.py', learn_facts.TREE_MAIN), set())
        self.assertEqual(nodes(DATA / 'inplace_slice.py', TREE_V03), {'sequence_transformation'})

    def test_near_shapes_unchanged(self):
        for name in ('neg_fib_vars.py', 'neg_halves.py', 'neg_slice_copy.py'):
            with self.subTest(file=name):
                self.assertEqual(nodes(DATA / name, TREE_V03), nodes(DATA / name, learn_facts.TREE_MAIN))

    def test_thealgorithms_quick_sort_unchanged(self):
        path = ROOT / 'data' / 'TheAlgorithms-Python' / 'sorts' / 'quick_sort.py'
        self.assertEqual(nodes(path, TREE_V03), nodes(path, learn_facts.TREE_MAIN))


class LispFinallyTests(unittest.TestCase):
    def test_finally_runs_after_the_loop(self):
        import crosslang_frontends
        import lisp_loop_v03
        crosslang_frontends.install(lisp_sbcl=False)
        lisp_loop_v03.install()
        import io_trace
        runs = io_trace.run_functions(DATA / 'fib_finally.lisp')['fib-loop']
        got = dict(zip([x[0] for x in runs['inputs']], [r[1] for r in runs['runs']]))
        self.assertEqual([got[n] for n in range(8)], ['0', '1', '1', '2', '3', '5', '8', '13'])


if __name__ == '__main__':
    unittest.main()

"""Uniform conversion (user: the same program component is the same Prolog term in every language): the
same algorithm written with the same structure in two languages reaches the same tree node (the normal
process's relations, learn_facts.nodes)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import learn_facts

DATA = ROOT / 'tests' / 'data' / 'uniform'
PAIRS = [
    ('cmp_le.py', 'cmp_gt.c'),                    # take if w <= cap  /  skip if w > cap; counting loops
    ('caesar_loop.py', 'caesar_loop.lisp'),       # ord / chr = char-code / code-char; append = push
    ('matrix_collect.py', 'matrix_collect.lisp'),  # append to a result = loop ... collect
    ('matrix_table.py', 'matrix_table.lisp'),     # [[0] * n ...] = make-array; c[i][j] = (aref c i j)
]


class UniformTests(unittest.TestCase):
    def test_same_component_same_term(self):
        for a, b in PAIRS:
            with self.subTest(pair=(a, b)):
                self.assertEqual(learn_facts.nodes(DATA / a), learn_facts.nodes(DATA / b))


class BuiltBranchTests(unittest.TestCase):
    def test_hanoi_built_branch(self):
        """Built branch (doc 04 section 15): f(n-1); move; f(n-1) is towers_of_hanoi in every language; the
        combined fib(n-1) + fib(n-2) stays fibonacci_like; a walk on left/right, Ackermann (its jump sets n to 1)
        and an edit distance (its call results are used) stay the broad branch."""
        import learn_apply
        for f, branch in [('hanoi.py', 'towers_of_hanoi'), ('hanoi.c', 'towers_of_hanoi'), ('hanoi.lisp', 'towers_of_hanoi'),
                          ('fib.py', 'fibonacci_like'), ('inorder.py', 'recursive_decomposition')]:
            with self.subTest(file=f):
                self.assertEqual(learn_apply.apply(DATA / f)[3], {branch})
        for f in ('ack.lisp', 'edit.lisp'):
            self.assertNotIn('towers_of_hanoi', learn_apply.apply(DATA / f)[3])


    def test_built_branches(self):
        """Built branches (doc 04 section 15): each task's relation holds in every language; close negatives do
        not get it."""
        import learn_apply
        cases = {'ackermann': (['ack.py', 'ack.c', 'ack.lisp'], ['mc91.py', 'fib.py']),
                 'towers_of_hanoi': (['hanoi.py', 'hanoi.c', 'hanoi.lisp', 'hanoi.hs'], ['fib.hs', 'fib.py', 'count_down.hs']),
                 'knapsack_01': (['knap.py', 'knap.c', 'knap_rec.py', 'knap_rec.hs'], ['lcs_table.py', 'matrix_table.py', 'count_down.hs']),
                 'caesar_cipher': (['caesar_loop.py', 'caesar_loop.lisp', 'caesar_pf.hs'], ['vigenere.py', 'fib.hs']),
                 'matrix_multiplication': (['matrix_table.py', 'matrix_table.lisp', 'matrix_collect.py', 'matrix_collect.lisp',
                                            'matrix_fn.lisp'],
                                           ['dot.py', 'knap.py']),
                 'run_length_encoding': (['rle_group.lisp', 'rle_scan.py'], ['dedup.py']),
                 'n_queens': (['queens_perm.py', 'queens_perm.hs', 'queens_bt.py', 'queens_bt.c', 'queens_fold.hs'],
                              ['perm_sort.py', 'grid_paths.py']),
                 'lcs': (['lcs_rec.py', 'lcs_rec.lisp', 'lcs_table.py', 'lcs_memo.hs'], ['lev_table.py', 'knap.py']),
                 'levenshtein': (['lev_table.py', 'lev_table.c'], ['lcs_table.py', 'lcs_rec.py']),
                 'roman_encode': (['roman_fmt.lisp'], ['plain_fmt.lisp'])}
        for task, (positives, negatives) in cases.items():
            for f in positives:
                with self.subTest(task=task, file=f):
                    self.assertIn(task, learn_apply.apply(DATA / f)[3])
            for f in negatives:
                with self.subTest(task=task, negative=f):
                    self.assertNotIn(task, learn_apply.apply(DATA / f)[3])


if __name__ == '__main__':
    unittest.main()

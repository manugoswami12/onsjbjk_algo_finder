"""Uniform conversion (user: the same program component is the same Prolog term in every language): the
same algorithm written with the same structure in two languages gives the same tree node and the same
logic-flow tokens (learn_facts.tree: the normal process's tree and the shared tokenizer)."""
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
                na, sa = learn_facts.tree(DATA / a)
                nb, sb = learn_facts.tree(DATA / b)
                self.assertEqual(na, nb)
                self.assertEqual([t for _, t in sa], [t for _, t in sb])


if __name__ == '__main__':
    unittest.main()

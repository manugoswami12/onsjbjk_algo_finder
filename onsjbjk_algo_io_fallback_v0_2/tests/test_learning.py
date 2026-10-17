"""Learning tests (doc 04): anti-unification, and learn-from-Python / apply-to-Lisp-and-C on own programs."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import learn_apply

DATA = ROOT / 'tests' / 'data' / 'learn'


class LearningTests(unittest.TestCase):
    def test_anti_unification(self):
        goal = ("lgg([a, op(add), b, c], [a, x, op(mul), c], G), print(G), nl, "
                "lgg([test, call('$self'), output, call('$self')], [test, ret, call('$self'), call(append), call('$self')], H), "
                "print(H), nl")
        out = subprocess.run(['swipl', '-q', '-g', f"consult('{ROOT / 'prolog' / 'learn_dcg.pl'}'), {goal}", '-t', 'halt'],
                             capture_output=True, text=True, check=True).stdout.split('\n')
        self.assertRegex(out[0], r"^\[a,op\(_\w*\),c\]$")
        self.assertEqual(out[1], "[test,call('$self'),call('$self')]")

    def test_learn_python_apply_lisp_and_c(self):
        with tempfile.TemporaryDirectory() as td:
            rules = Path(td) / 'rules.pl'
            learn_apply.learn({DATA / 'hanoi_a.py': 'towers_of_hanoi', DATA / 'hanoi_b.py': 'towers_of_hanoi',
                               DATA / 'neg_fib.py': None, DATA / 'neg_sum.py': None, DATA / 'neg_gcd.py': None}, rules)
            for f in ('hanoi_test.lisp', 'hanoi_test.c'):
                self.assertEqual({lab for _, lab, _ in learn_apply.apply(DATA / f, rules)}, {'towers_of_hanoi'}, f)
            for f in ('fib_test.lisp', 'sum_test.c'):
                self.assertEqual(learn_apply.apply(DATA / f, rules), [], f)


if __name__ == '__main__':
    unittest.main()

"""Learning tests (doc 04): the pattern relation in both directions, and learn-from-Python / apply-to-Lisp-and-C on own programs."""
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
    def test_pattern_both_directions(self):
        """pattern//1 like sum/3: S known -> does the stream hold it; S unbound -> the skeleton streams share;
        a helper's name is a variable, so two files' helpers unify."""
        goal = ("( phrase(pattern([a, link(G), b, leave(G)]), [x, a, link(go), y, b, leave(go)], _) -> writeln(G) ; writeln(no) ), "
                "( phrase(pattern([a, b]), [b, a], _) -> writeln(yes) ; writeln(no) ), "
                "shared([[a, b, link(X), c, leave(X), d], [a, z, link(Y), c, leave(Y), b, d]], S), print(S), nl")
        out = subprocess.run(['swipl', '-q', '-g', f"consult('{ROOT / 'prolog' / 'learn_dcg.pl'}'), {goal}", '-t', 'halt'],
                             capture_output=True, text=True, check=True).stdout.split('\n')
        self.assertEqual(out[:2], ['go', 'no'])
        self.assertRegex(out[2], r"^\[a,link\((_\w*)\),c,leave\(\1\),d\]$")

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

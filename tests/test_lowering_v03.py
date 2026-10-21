"""lowering_v03.py (installed by crosslang_frontends, doc 04 section 19.4): two semantics fixes of the behaviour lowering, the
same for every program. The Lisp loop's `finally` runs once after the loop; C's `x op= y` keeps its operator."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import crosslang_frontends
import lowering_v03

DATA = ROOT / 'tests' / 'data' / 'v03'


def outputs(path: Path, name: str) -> list[str]:
    import io_trace
    runs = io_trace.run_functions(path)[name]
    got = dict(zip([x[0] for x in runs['inputs']], [r[1] for r in runs['runs']]))
    return [got[n] for n in range(8)]


class LoweringV03Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        crosslang_frontends.install(lisp_sbcl=False)
        lowering_v03.install()

    def test_lisp_finally_runs_after_the_loop(self):
        self.assertEqual(outputs(DATA / 'fib_finally.lisp', 'fib-loop'), ['0', '1', '1', '2', '3', '5', '8', '13'])

    def test_c_compound_assignment_keeps_its_operator(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / 'prod.c'
            src.write_text('int prod(int n) { int r = 1; for (int i = 1; i <= n; ++i) r *= i; return r; }\n')
            self.assertEqual(outputs(src, 'prod'), ['1', '1', '2', '6', '24', '120', '720', '5040'])


if __name__ == '__main__':
    unittest.main()

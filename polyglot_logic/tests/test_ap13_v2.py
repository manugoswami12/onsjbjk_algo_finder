"""AP13 v2 tests (doc 04 B1-B6): general learning from every function.

Uses only the committed examples/v2 files (no corpus or Rosetta checkout needed).
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
V2 = ROOT / 'examples' / 'v2'
sys.path.insert(0, str(TOOLS))

HAVE_TS = importlib.util.find_spec('tree_sitter_language_pack') is not None
HAVE_SWIPL = shutil.which('swipl') is not None


def facts(path):
    from cli import facts_text
    return facts_text(path)[1]


@unittest.skipUnless(HAVE_TS, 'tree-sitter-language-pack not installed')
class LoweringV2(unittest.TestCase):
    def test_recursion_is_a_loop_with_self_calls_and_parameter_updates(self):
        text = facts(V2 / 'candidates' / 'gcd.rs')
        self.assertIn("'recursion'", text)
        self.assertIn("'$self'", text)
        self.assertIn("assign('s3','var'('a'),'var'('b'))", text)

    def test_conditional_expression_becomes_guarded_returns(self):
        text = facts(V2 / 'reference' / 'maths.py')
        self.assertIn("'op'('mul',['var'('n'),'call'('$self'", text)

    def test_input_validation_is_not_control_dependence(self):
        text = facts(V2 / 'reference' / 'maths.py')
        self.assertNotIn("guard('s3','op'('lt',['var'('n'),'int'(0)])", text)
        self.assertNotIn("'lt',['var'('n'),'int'(0)]),'false'", text)

    def test_haskell_fold_is_an_accumulator_loop(self):
        text = facts(V2 / 'candidates' / 'hash.hs')
        self.assertIn("loop_iter(", text)
        self.assertIn("'$acc'", text)
        self.assertIn("'call'('ord'", text)          # fromEnum -> ord (synonym table)

    def test_docstrings_are_ignored(self):
        self.assertNotIn("unsupported(", facts(V2 / 'reference' / 'maths.py'))


@unittest.skipUnless(HAVE_TS and HAVE_SWIPL, 'needs tree-sitter-language-pack and swipl')
class GeneralLearningV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory(prefix='ap13_v2_')
        cls.store = Path(cls.td.name)
        r = subprocess.run([sys.executable, str(TOOLS / 'cli.py'), '--store', str(cls.store),
                            'learn-dir', str(V2 / 'reference')], capture_output=True, text=True, timeout=600)
        assert r.returncode == 0, r.stdout + r.stderr
        cls.learn_out = r.stdout

    @classmethod
    def tearDownClass(cls):
        cls.td.cleanup()

    def top(self, name):
        from cli import scan
        r = scan(V2 / 'candidates' / name, self.store, True, quiet=True)
        m = [x['label'] for x in r['leaves'] if x['result'] == 'MATCH']
        return m[0].split('__')[-1] if m else None

    def test_B2_every_function_is_learned_or_classified(self):
        self.assertIn('usable=4', self.learn_out)
        self.assertIn('trivial=1', self.learn_out)     # add(a, b): no loop, not an algorithm

    def test_B2_learning_is_idempotent(self):
        r = subprocess.run([sys.executable, str(TOOLS / 'cli.py'), '--store', str(self.store),
                            'learn-dir', str(V2 / 'reference')], capture_output=True, text=True, timeout=600)
        self.assertIn('already_present=5', r.stdout)

    def test_iterative_factorial_python_to_c(self):
        self.assertEqual(self.top('factorial.c'), 'factorial')

    def test_recursive_factorial_python_to_lisp(self):
        self.assertEqual(self.top('factorial.lisp'), 'factorial_recursive')

    def test_gcd_python_to_rust_and_haskell_despite_argument_order(self):
        self.assertEqual(self.top('gcd.rs'), 'gcd')
        self.assertEqual(self.top('gcd.hs'), 'gcd')

    def test_hash_python_to_haskell_foldl(self):
        self.assertEqual(self.top('hash.hs'), 'poly_hash')

    def test_different_logic_is_not_claimed(self):
        self.assertIsNone(self.top('djb2.py'))       # other hash recurrence
        self.assertIsNone(self.top('sum_list.c'))    # sum of elements is not factorial


if __name__ == '__main__':
    unittest.main()

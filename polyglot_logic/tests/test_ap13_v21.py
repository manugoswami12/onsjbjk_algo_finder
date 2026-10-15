"""AP13 v2.1 tests (doc 07): sound copy propagation, library folds, R calls,
prefilter soundness, and the validate / generalize commands.

Uses only the committed examples/v2 and examples/v21 files.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
V2 = ROOT / 'examples' / 'v2'
V21 = ROOT / 'examples' / 'v21'
sys.path.insert(0, str(TOOLS))

HAVE_TS = importlib.util.find_spec('tree_sitter_language_pack') is not None
HAVE_SWIPL = shutil.which('swipl') is not None


def facts(path):
    from cli import facts_text
    return facts_text(path)[1]


@unittest.skipUnless(HAVE_TS, 'tree-sitter-language-pack not installed')
class LoweringV21(unittest.TestCase):
    def test_library_fold_is_an_accumulator_loop(self):
        text = facts(V21 / 'fold_factorial.py')
        self.assertIn("loop_iter(", text)
        self.assertIn("'op'('mul',['var'('$acc", text)
        self.assertIn("ret('s2','var'('$acc", text)

    def test_r_call_separators_are_not_arguments(self):
        text = facts(V21 / 'swap.r')
        self.assertNotIn("'comma'", text)
        self.assertIn("'call'('c',['var'('i'),'op'('add',['var'('i'),'int'(1)])])", text)

    def test_recursive_function_with_element_writes_lowers(self):
        # parameter updates are de-duplicated by rendered term (terms hold lists)
        text = facts(V21 / 'recursive_write.py')
        self.assertIn("assign('s4','var'('i'),'op'('add',['var'('i'),'int'(1)]))", text)

    def test_prefilter_keeps_index_shift_family(self):
        from knowledge_store import fact_features
        have = fact_features("assign('s1','elem'('var'('a'),'op'('sub',['var'('i'),'int'(1)])),'int'(0)).")
        self.assertIn('op:add', have)


@unittest.skipUnless(HAVE_TS and HAVE_SWIPL, 'needs tree-sitter-language-pack and swipl')
class TracingV21(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory(prefix='ap13_v21_')
        self.store = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def learned(self, label, src, fn):
        from cli import learn
        learn(label, src, fn, self.store)
        return (self.store / 'patterns' / f'{label}.pl').read_text(encoding='utf-8')

    def test_copy_is_not_propagated_across_a_redefinition(self):
        # key = a[i] reaches a[i] = key only through the shifting loop that rewrites a and i:
        # the reference must keep `key`, never the unsound a[i] = a[i]
        ref = self.learned('ins', V21 / 'insertion_sort.py', 'insertion_sort')
        self.assertNotRegex(ref, r'value\((\w+), elem\(var\((\w+)\), var\((\w+)\)\), elem\(var\(\2\), var\(\3\)\)\)')
        self.assertRegex(ref, r'value\(\w+, elem\(var\(\w+\), var\(\w+\)\), var\(\w+\)\)')

    def test_fold_factorial_matches_loop_factorial_but_list_product_does_not(self):
        from cli import scan
        self.learned('loop_factorial', V21 / 'loop_factorial.py', 'factorial')
        r = scan(V21 / 'fold_factorial.py', self.store, True, quiet=True)
        funcs = {x['functions'] for x in r['leaves'] if x['result'] == 'MATCH'}
        self.assertIn('factorial', funcs)
        self.assertNotIn('product_of', funcs)

    def test_validate_and_generalize_commands_run(self):
        from cli import generalize, learn_dir, validate
        learn_dir(V2 / 'reference', self.store, 100)
        counts = validate(V2 / 'reference', self.store, workers=2)
        self.assertGreaterEqual(counts.get('usable', 0), 1)
        self.assertNotIn('generic', counts)          # one file cannot be "unrelated code"
        self.assertIn('variant_pairs_files', generalize(V2 / 'reference', self.store, workers=2))


if __name__ == '__main__':
    unittest.main()

"""AP13 v3.1 tests (doc 09): one explained outcome per file, new branches, single answer."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
V3 = ROOT / 'examples' / 'v3'

HAVE_TS = importlib.util.find_spec('tree_sitter_language_pack') is not None
HAVE_SWIPL = shutil.which('swipl') is not None


@unittest.skipUnless(HAVE_TS and HAVE_SWIPL, 'needs tree-sitter-language-pack and swipl')
class Outcomes(unittest.TestCase):
    def test_expected_outcomes(self):
        from outcome import classify
        truth = {k: v for k, v in json.loads((V3 / 'expected_outcomes.json').read_text()).items()
                 if not k.startswith('_')}
        for rel, exp in truth.items():
            got = classify(V3 / rel, None, {})
            self.assertEqual(got['outcome'], exp['outcome'], rel)
            if 'family' in exp:
                self.assertEqual(got['family'], [tuple(exp['family'])], rel)
            if 'reason' in exp:               # the frozen key words must be in the stated reason
                self.assertIn(exp['reason'].split(' only')[0].split(' (')[0], got['reason'], rel)

    def test_new_branches_on_own_cases(self):
        from family_scan import answers
        exp = {'c23_palindrome.py': ['sequence_query', 'predicate', 'symmetric_compare'],
               'c24_caesar.c': ['sequence_transformation', 'elementwise_map'],
               'c25_rle.java': ['sequence_transformation', 'construction', 'run_length'],
               'c26_queens.py': ['search', 'backtracking'],
               'c27_roman.rs': ['numeric', 'decomposition', 'greedy_denominations'],
               'c28_josephus.hs': ['numeric', 'recurrence', 'josephus_recurrence'],
               'c29_pancake.c': ['sequence_transformation', 'comparison_sort', 'prefix_reversal']}
        for f, path in exp.items():
            got = [p for ps in answers(V3 / 'cases' / f).values() for p in ps]
            self.assertEqual(got, [path], f)

    def test_helpers_are_not_the_answer(self):
        from family_scan import answers
        self.assertEqual(sorted(answers(V3 / 'cases' / 'c29_pancake.c')), ['pancake'])   # not flip
        self.assertEqual(sorted(answers(V3 / 'cases' / 'c36_helpers.py')), ['selection'])

    def test_definitions_never_reported_as_no_body(self):
        from outcome import source_definitions
        self.assertGreater(source_definitions(V3 / 'cases' / 'c28_josephus.hs'), 0)
        self.assertEqual(source_definitions(V3 / 'cases' / 'c32_fragment.lisp'), 0)


if __name__ == '__main__':
    unittest.main()

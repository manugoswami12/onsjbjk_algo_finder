"""AP13 v3 tests (doc 08): input->output family branching, added beside the exact matcher.

Uses only the committed examples/v3 files (own code, 8 languages).
"""
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
class FamilyBranching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from family_scan import answers as families   # one answer per file (doc 09)
        truth = json.loads((V3 / 'expected_families.json').read_text())
        cls.truth = {k: v for k, v in truth.items() if not k.startswith('_')}
        cls.got = {rel: [p for ps in families(V3 / rel).values() for p in ps] for rel in cls.truth}

    def test_every_case_reaches_its_expected_family(self):
        for rel, expected in self.truth.items():
            self.assertIn(expected, self.got[rel], rel)

    def test_no_case_gets_a_contradicting_family(self):
        for rel, expected in self.truth.items():
            for p in self.got[rel]:
                self.assertEqual(expected[:len(p)], p, f'{rel}: {p}')

    def test_cases_cover_all_eight_languages(self):
        self.assertEqual({Path(r).suffix for r in self.truth},
                         {'.c', '.java', '.rs', '.hs', '.py', '.r', '.lisp', '.pl'})

    def test_collatz_remainder_test_is_not_digit_decomposition(self):
        self.assertNotIn(['numeric', 'decomposition', 'digits'], self.got['cases/c17_collatz.r'])

    def test_family_layer_does_not_change_exact_matching(self):
        # the exact path still answers through the unchanged cli.scan
        import tempfile
        from cli import learn, scan
        with tempfile.TemporaryDirectory() as td:
            learn('bubble', ROOT / 'examples' / 'bubble' / 'bubble.py', 'bubble_sort', Path(td))
            r = scan(V3 / 'cases' / 'c01_bubble.c', Path(td), True, quiet=True)
            self.assertIn('bubble', {x['label'] for x in r['leaves'] if x['result'] == 'MATCH'})


if __name__ == '__main__':
    unittest.main()

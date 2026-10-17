"""Logic tests: small Lisp functions compiled by ECL, traced by prolog/ecl_main.pl (AP13 rules)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import ecl_compile
import ecl_facts
import ecl_fallback
import ecl_logic

EXPECTED = {
    'gcd2': 'euclid_like', 'gcdr': 'euclid_like', 'fact': 'factorial_like', 'facti': 'factorial_like',
    'fib': 'fibonacci_like', 'dsum': 'digit_processing', 'isort': 'comparison_driven_reordering',
    'csort': 'comparison_driven_reordering', 'shsort': 'shift_insertion', 'ssort': 'selection_exchange',
    'vsel': 'selection_exchange', 'lsum': 'element_accumulation', 'pal': 'palindrome_check',
    'qsl': 'comparison_driven_reordering', 'rfact': 'factorial_like', 'rsum': 'series_sum',
    'fibl': 'fibonacci_like', 'bsr': 'interval_lookup', 'bsieve': 'sieve_like',
    'dotl': 'element_accumulation', 'dsumb': 'digit_processing', 'msort': 'comparison_driven_reordering',
    'mergel': None, 'bsk': 'interval_lookup', 'bss': 'interval_lookup',
    'facta': 'factorial_like', 'gsort': 'comparison_driven_reordering', 'm2max': 'extremum_search', 'pass': 'comparison_driven_reordering',   # closure comparator 'bsearch': 'interval_lookup', 'vmax': 'extremum_search', 'vsum': 'element_accumulation',
    # near misses: no v0.2 branch
    'twice': None, 'countdown': None, 'vcopy': None, 'lastel': None, 'addmod': None, 'countup': None, 'lcount': None, 'squares': None,
    'inrange': None, 'shiftc': None, 'applyf': None,
    'vrev': 'sequence_rearrangement',   # a reversal: rearranged, never compared (no comparison sort)
}


class EclLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fams = ecl_logic.families(ROOT / 'tests' / 'data' / 'ecl_logic.lisp')
        cls.branches = {name: {b for _, b in fams.get(name, [])} - {'none'} for name in EXPECTED}

    def test_condition_is_read_from_the_tree(self):
        # (<= 97 c 122) is 97 <= c && c <= 122: ECL's (v3c) && (v3c) is not a cast
        facts = ecl_facts.facts_of(ecl_compile.ecl_units(ROOT / 'tests' / 'data' / 'ecl_logic.lisp'))
        self.assertNotIn('pointer_expression', facts)

    def test_no_algorithm_files(self):
        data = ROOT / 'tests' / 'data'
        self.assertIn(ecl_logic.NOCODE, ecl_logic.families(data / 'nocode_driver.lisp'))
        self.assertIn(ecl_logic.NOCODE, ecl_logic.families(data / 'nocode_repl.lisp'))
        fams = ecl_logic.families(data / 'toplevel_fib.lisp')
        self.assertNotIn(ecl_logic.NOCODE, fams)
        self.assertIn('fibonacci_like', {b for v in fams.values() for _, b in v})

    def test_inlined_index_helpers(self):
        fams = ecl_logic.families(ROOT / 'tests' / 'data' / 'heap_helpers.lisp')
        self.assertIn('sequence_transformation>comparison_sort>heap', {f for f, _ in fams['hsort']})
        self.assertNotIn('comparison_driven_reordering', {b for _, b in fams['usesq']})

    def test_fallback(self):
        data = ROOT / 'tests' / 'data'
        normal, export = ecl_logic.trace(data / 'fallback_fold.lisp')
        found = ecl_fallback.answers(export)               # ping/pong: the link walk terminates
        self.assertEqual(found.get('dotv'), [('element_accumulation', 'fold_map')])
        self.assertNotIn('mapped', found)                  # a map without a fold: no aggregate
        self.assertNotIn('vsum2', found)                   # answered by the normal process
        self.assertIn('element_accumulation', {b for _, b in normal['vsum2']})
        _, export = ecl_logic.trace(data / 'fallback_insert.lisp')
        self.assertEqual(ecl_fallback.answers(export).get('fsort'), [('shift_insertion', 'fold_ordered_insert')])
        _, export = ecl_logic.trace(data / 'fallback_pancake.lisp')
        found = ecl_fallback.answers(export)
        self.assertEqual(found.get('psort'), [('comparison_driven_reordering', 'prefix_reversal')])
        self.assertNotIn('maxpos', found)                  # the extreme's position, never flipped
        _, export = ecl_logic.trace(data / 'fallback_recinsert.lisp')
        found = ecl_fallback.answers(export)
        self.assertEqual(found.get('risort'), [('shift_insertion', 'recursive_ordered_insert')])
        self.assertNotIn('rcopy', found)                   # recursion over a copy: no comparison
        _, export = ecl_logic.trace(data / 'fallback_noorder.lisp')
        self.assertEqual(ecl_fallback.answers(export), {})   # an insertion without a comparison

    def test_branches(self):
        for name, want in EXPECTED.items():
            with self.subTest(name=name):
                self.assertEqual(self.branches[name], {want} if want else set())


if __name__ == '__main__':
    unittest.main()

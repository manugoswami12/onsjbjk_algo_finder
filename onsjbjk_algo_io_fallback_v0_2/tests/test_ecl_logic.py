"""Logic tests: small Lisp functions compiled by ECL, traced by prolog/ecl_main.pl (AP13 rules)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import ecl_compile
import ecl_facts
import ecl_logic

EXPECTED = {
    'gcd2': 'euclid_like', 'gcdr': 'euclid_like', 'fact': 'factorial_like', 'facti': 'factorial_like',
    'fib': 'fibonacci_like', 'dsum': 'digit_processing', 'isort': 'comparison_driven_reordering',
    'csort': 'comparison_driven_reordering', 'shsort': 'shift_insertion', 'ssort': 'selection_exchange',
    'vsel': 'selection_exchange', 'lsum': 'element_accumulation', 'pal': 'palindrome_check',
    'qsl': 'comparison_driven_reordering', 'rfact': 'factorial_like', 'rsum': 'series_sum',
    'fibl': 'fibonacci_like', 'bsr': 'interval_lookup', 'bsieve': 'sieve_like',
    'dotl': 'element_accumulation', 'bsearch': 'interval_lookup', 'vmax': 'extremum_search', 'vsum': 'element_accumulation',
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

    def test_branches(self):
        for name, want in EXPECTED.items():
            with self.subTest(name=name):
                self.assertEqual(self.branches[name], {want} if want else set())


if __name__ == '__main__':
    unittest.main()

"""Library-name fallback (doc 04 section 18.1, prolog/library_names.pl): a program whose computation is one library
call is named by that library's algorithm in every language; a library call inside other code names nothing."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import crosslang_frontends
import ta_library

DATA = ROOT / 'tests' / 'data' / 'library'
POSITIVE = {'fact_wrap.py': 'factorial', 'gcd_script.py': 'gcd', 'sort_inplace.py': 'sorting',
            'sort_wrap.hs': 'sorting', 'gcd_wrap.hs': 'gcd', 'lcm_repl.lisp': 'lcm', 'sort_wrap.lisp': 'sorting',
            'qsort_wrap.c': 'sorting'}
NEGATIVE = ['neg_rho.py', 'neg_ncr.py', 'neg_median.py', 'neg_bubble_check.py', 'neg_own_factorial.py',
            'neg_sort_key.hs', 'neg_lcm_of_list.lisp']


class LibraryNameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        crosslang_frontends.install(lisp_sbcl=False)

    def test_positive(self):
        for name, alg in POSITIVE.items():
            with self.subTest(file=name):
                self.assertEqual(ta_library.algorithm(DATA / name), alg)

    def test_negative(self):
        for name in NEGATIVE:
            with self.subTest(file=name):
                self.assertIsNone(ta_library.algorithm(DATA / name))


if __name__ == '__main__':
    unittest.main()

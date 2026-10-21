"""Conversion faults of our own layer and rules carried over from another language (doc 04 section 19.14):
a multi-line Haskell import moved as a whole (haskell_core_pnf.prepared_source); C macros expanded for behaviour as
for the tree (learn_facts.c_expanded); a definition whose GHC type takes more arguments than its equation, eta-expanded
(haskell_core_pnf.typed_eta), and GHC's out-of-scope names; a Python generator as the list it yields (generators.py); Python's extended
slice store and floor division (prolog/interp_v04.pl)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import crosslang_frontends

crosslang_frontends.install(lisp_sbcl=False)
import haskell_core_pnf
import io_trace


def runs(name, text, fn):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / name
        p.write_text(text, encoding='utf-8')
        d = io_trace.run_functions(p)[fn]
        return {tuple(a): r[1] for a, r in zip(d['inputs'], d['runs'])}


class OwnLayerRules(unittest.TestCase):
    def test_multiline_import_moves_whole(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.hs'
            p.write_text('import Data.List ( sort,\n                   nub )\nf :: [Int] -> [Int]\nf = sort . nub\n')
            src = haskell_core_pnf.prepared_source(p)
        self.assertIn('import Data.List ( sort,\n                   nub )', src)
        self.assertLess(src.index('nub )'), src.index('f ::'))

    def test_c_macros_expanded_for_behaviour(self):
        r = runs('m.c', '#define K 7\nint f(int n) { return n % K; }\n', 'f')
        self.assertEqual(r[(10,)], '3')

    def test_arity_from_ghc_types(self):
        types = 'TYPE SIGNATURES\n  digsum :: forall a. Integral a => a -> a -> a\n  g :: (Ord a, Num a) => (a -> a) -> [a] -> Int\n  k :: Maybe (Int -> Int)\n'
        self.assertEqual(haskell_core_pnf.type_arities(types), {'digsum': 2, 'g': 2, 'k': 0})

    def test_partly_applied_root_is_eta_expanded_by_its_type(self):
        funs = [('f', ['b', 'a', 'n'], ('seq', [('return', ('op', 'add', [('var', 'a'), ('var', 'n')]))])),
                ('digsum', ['b'], ('seq', [('return', ('call', 'f', [('var', 'b'), ('int', 0)]))]))]
        out = dict((n, (ps, body)) for n, ps, body in haskell_core_pnf.typed_eta(funs, {'digsum': 2}))
        self.assertEqual(out['digsum'][0], ['b', 'eta$0'])
        self.assertEqual(out['digsum'][1], ('seq', [('return', ('call', 'f', [('var', 'b'), ('int', 0), ('var', 'eta$0')]))]))
        self.assertEqual(haskell_core_pnf.typed_eta(funs, {'digsum': 1}), funs)

    def test_sum_digits_root_runs(self):
        r = runs('m.hs', 'digsum :: Integral a => a -> a -> a\ndigsum base = f 0\n  where\n    f a 0 = a\n'
                 '    f a n = f (a + r) q\n      where\n        (q, r) = n `quotRem` base\n', 'digsum')
        self.assertEqual(r[(12, 18)], '7')          # 18 is 16 in base 12

    def test_out_of_scope_names_from_ghc(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.hs'
            p.write_text('f :: Int -> Int\nf n = n + missingName\n')
            funs = haskell_core_pnf.haskell_normal_form(p)
        self.assertIn("not_in_scope(missingName)", str(funs))

    def test_generator_gives_the_list_it_yields(self):
        r = runs('g.py', 'def g(n):\n    yield 1\n    if n < 2: return\n    for i in range(n):\n        yield i * i\n', 'g')
        self.assertEqual(r[(1,)], '[1]')
        self.assertEqual(r[(4,)], '[1,0,1,4,9]')

    def test_only_python_generators_are_lists(self):
        r = runs('h.py', 'def h(n):\n    def inner():\n        yield n\n    return [n]\n', 'h')
        self.assertEqual(r[(3,)], '[3]')

    def test_extended_slice_store_and_floor_division(self):
        src = 'def f(n):\n    b = [1] * n\n    b[2::3] = [0] * ((n - 3) // 3 + 1)\n    b[::-2] = [7] * ((n + 1) // 2)\n    return b\n'
        r = runs('s.py', src, 'f')
        self.assertEqual(r[(1,)], '[7]')
        self.assertEqual(r[(8,)], '[1,7,0,7,1,7,1,7]')


if __name__ == '__main__':
    unittest.main()

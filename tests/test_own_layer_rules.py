"""Conversion faults of our own layer and rules carried over from another language (doc 04 section 19.14):
a multi-line Haskell import moved as a whole (haskell_core_pnf.prepared_source); C macros expanded for behaviour as
for the tree (learn_facts.c_expanded); a definition returning a function partly applied, eta-expanded
(crosslang_frontends.eta_expanded); a Python generator as the list it yields (generators.py); Python's extended
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

    def test_partly_applied_root_is_eta_expanded(self):
        funs = [('g', ['b', 'a', 'n'], ('seq', [('return', ('op', 'add', [('var', 'a'), ('var', 'n')]))])),
                ('h', ['b'], ('seq', [('return', ('call', 'g', [('var', 'b'), ('int', 0)]))]))]
        out = dict((n, (ps, body)) for n, ps, body in crosslang_frontends.eta_expanded(funs))
        self.assertEqual(out['h'][0], ['b', 'eta$0'])
        self.assertEqual(out['h'][1], ('seq', [('return', ('call', 'g', [('var', 'b'), ('int', 0), ('var', 'eta$0')]))]))
        self.assertEqual(out['g'][0], ['b', 'a', 'n'])

    def test_value_return_unchanged(self):
        funs = [('h', ['n'], ('seq', [('return', ('var', 'n'))]))]
        self.assertEqual(crosslang_frontends.eta_expanded(funs), funs)

    def test_generator_gives_the_list_it_yields(self):
        r = runs('g.py', 'def g(n):\n    yield 1\n    if n < 2: return\n    for i in range(n):\n        yield i * i\n', 'g')
        self.assertEqual(r[(1,)], '[1]')
        self.assertEqual(r[(4,)], '[1,0,1,4,9]')

    def test_extended_slice_store_and_floor_division(self):
        src = 'def f(n):\n    b = [1] * n\n    b[2::3] = [0] * ((n - 3) // 3 + 1)\n    b[::-2] = [7] * ((n + 1) // 2)\n    return b\n'
        r = runs('s.py', src, 'f')
        self.assertEqual(r[(1,)], '[7]')
        self.assertEqual(r[(8,)], '[1,7,0,7,1,7,1,7]')


if __name__ == '__main__':
    unittest.main()

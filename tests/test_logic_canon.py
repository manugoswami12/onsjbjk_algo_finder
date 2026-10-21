"""The canonical view of the traced-logic tier (doc 04 section 19.13): prolog/logic_canon.pl drops an input check that
guards every statement of a pattern and makes a range bound a variable, on the term (the pattern's variable list keeps
only its variables); eval_ta.CanonicalLogic matches perfect-numbers-1.hs to TheAlgorithms' perfect()."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import logic_canon

PERFECT = ('reference(p, unknown, [cret(A, op(eq, [var(B), var(C)])), nguard(A, op(ge, [int(0), var(C)]), false), '
           'value(D, var(B), op(add, [var(B), elem(filter(call(range, [int(1), op(add, [op(div, [var(C), int(2)]), '
           'int(1)])]), op(eq, [op(mod, [var(C), elem(call(range, [int(1), op(add, [op(div, [var(C), int(2)]), int(1)])]), '
           'var(E))]), int(0)])), var(F))])), under(D, G), lvar(G, var(F)), nguard(D, op(ge, [int(0), var(C)]), false), '
           'seed(var(B), int(0))], [B, F, E, C]).')
PARTLY = ('reference(q, unknown, [cret(A, var(B)), nguard(A, op(gt, [int(10), var(C)]), false), value(D, var(B), var(C)), '
          'cret(_, call(range, [int(1), op(add, [var(I), int(1)])]))], [B, C, I]).')


class LogicCanonTests(unittest.TestCase):
    def test_an_input_check_on_every_statement_and_the_range_bound_go(self):
        out = logic_canon.canonical_terms([PERFECT])[0]
        self.assertNotIn('nguard', out)
        self.assertNotIn('op(div', out)
        self.assertIn('call(range, [int(1), ', out)

    def test_a_guard_not_on_every_statement_stays_and_vars_are_the_clause_s(self):
        out = logic_canon.canonical_terms([PARTLY])[0]
        self.assertIn('nguard', out)                       # the value statement D is not guarded
        self.assertTrue(out.rstrip().endswith('[B, C]).'), out)   # I left with the range bound it named
        self.assertNotIn('var(I)', out)

    def test_learn_output_blocks_keep_their_order(self):
        lines = ['LEARN|p|unknown|7|usable|perfect', PERFECT, 'END', 'LEARN|q|unknown|4|usable|q', PARTLY, 'END']
        out = logic_canon.canonical_lines(lines)
        self.assertEqual([l for l in out if l.startswith(('LEARN', 'END'))], [lines[0], 'END', lines[3], 'END'])


if __name__ == '__main__':
    unittest.main()

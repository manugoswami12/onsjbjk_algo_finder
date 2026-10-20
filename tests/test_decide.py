"""prolog/decide.pl through eval_ta.decide: the tiers are tried in tier/2's order (file rule, built, trace, learned,
canonical, io); the first naming anything decides; several groups there are UNKNOWN; inside a tier no order counts."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import eval_ta

LABELS = {'a', 'b', 'c'}


def decide(spec=(), built=(), trace=(), held=(), io=(), canonical=()):
    out = {'nodes': [], 'held': list(held), 'held_trace': list(trace), 'io': list(io), 'logic': [],
           'canonical': list(canonical)}
    r = eval_ta.decide(out, set(built), set(spec), LABELS, {'c': 'a'})
    return r['got'], r['why'], r.get('clash')


class DecideTests(unittest.TestCase):
    def test_first_tier_naming_anything_decides(self):
        self.assertEqual(decide(spec=['a'], built=['b'], io=['c']), ('a', 'file_rule', None))
        self.assertEqual(decide(built=['b'], trace=['a']), ('b', 'built', None))
        self.assertEqual(decide(held=['b'], io=['a']), ('b', 'learned', None))
        self.assertEqual(decide(io=['b']), ('b', 'io', None))

    def test_canonical_logic_after_learned_before_behaviour(self):     # doc 04 section 19.13
        self.assertEqual(decide(held=['b'], canonical=['a']), ('b', 'learned', None))
        self.assertEqual(decide(canonical=['a'], io=['b']), ('a', 'canonical', None))

    def test_several_groups_at_the_deciding_tier_is_unknown(self):
        self.assertEqual(decide(trace=['b', 'a'], held=['a']), (None, 'ambiguous', ['a', 'b']))

    def test_labels_of_one_group_are_one_answer(self):
        self.assertEqual(decide(io=['a', 'c']), ('a', 'io', None))

    def test_nothing_is_none(self):
        self.assertEqual(decide(), (None, 'none', None))


if __name__ == '__main__':
    unittest.main()

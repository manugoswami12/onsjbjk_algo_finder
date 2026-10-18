"""Learning tests (doc 04 section 14): a learned branch sits at the tree node its Python file reaches and holds
exactly where a file at that node has the label's input->output behaviour (relations and behaviour only)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import learn_apply

DATA = ROOT / 'tests' / 'data' / 'uniform'


class LearningTests(unittest.TestCase):
    def test_branch_at_node_holds_by_behaviour(self):
        with tempfile.TemporaryDirectory() as td:
            rules = Path(td) / 'rules.pl'
            learn_apply.learn({DATA / 'cmp_le.py': 'capped_sum', DATA / 'matrix_table.py': None}, rules)
            text = rules.read_text(encoding='utf-8')
            self.assertIn("learned_branch([sequence_query, aggregate, gatherer], capped_sum, io, io)", text)
            nodes, found, at, _ = learn_apply.apply(DATA / 'cmp_gt.c', rules, io_labels={'capped_sum'})
            self.assertEqual((nodes, at), (['sequence_query>aggregate>gatherer'], {'capped_sum'}))
            self.assertEqual([lab for _, lab, _ in found], ['capped_sum'])
            self.assertEqual(learn_apply.apply(DATA / 'cmp_gt.c', rules)[1], [])          # no equal behaviour
            self.assertEqual(learn_apply.apply(DATA / 'matrix_table.lisp', rules, {'capped_sum'})[1], [])  # other node


if __name__ == '__main__':
    unittest.main()

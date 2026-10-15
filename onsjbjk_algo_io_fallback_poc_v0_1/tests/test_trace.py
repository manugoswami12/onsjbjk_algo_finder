"""No candidate Python file is imported; tests use source text only."""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from static_trace import analyze_source  # noqa: E402
from run_poc import facts_from  # noqa: E402


class EvidenceTests(unittest.TestCase):
    def analyse(self, name):
        return analyze_source((ROOT/'examples'/name).read_text(encoding='utf-8'))[0]

    def test_comparison_controls_actual_exchange(self):
        a = self.analyse('bubble.py')
        self.assertIn('comparison_controls_exchange', a.evidence)
        self.assertIn('returned_input', a.evidence)
        self.assertEqual(a.inputs, ['numbers'])

    def test_reverse_not_called_comparison_sort(self):
        a = self.analyse('reverse.py')
        self.assertIn('element_exchange', a.evidence)
        self.assertNotIn('comparison_controls_exchange', a.evidence)

    def test_wrong_exchange_does_not_count(self):
        self.assertNotIn('element_exchange', self.analyse('wrong_exchange.py').evidence)

    def test_input_and_output_link(self):
        a = self.analyse('binary.py')
        self.assertIn('sequence', a.dependencies['end'])
        self.assertIn('sequence', a.dependencies['center'])
        self.assertIn('indexed_equality_controls_index_return', a.evidence)
        self.assertIn('coherent_midpoint_interval_update', a.evidence)

    def test_linear_no_interval(self):
        a = self.analyse('linear.py')
        self.assertIn('indexed_equality_controls_index_return', a.evidence)
        self.assertNotIn('coherent_midpoint_interval_update', a.evidence)

    def test_dead_source_no_false_evidence(self):
        self.assertNotIn('element_exchange', self.analyse('dead_swap.py').evidence)

    def test_mismatched_condition_and_target(self):
        self.assertNotIn('comparison_controls_exchange', self.analyse('unrelated_array.py').evidence)

    def test_facts_are_anonymous_and_safely_formed(self):
        a = analyze_source('def evil_x(a):\n    return a\n')
        facts = facts_from(a)
        self.assertIn('program(f1, anonymous).', facts)
        self.assertNotIn('evil_x', facts)
        self.assertIn('observed(f1, returned_input, 2).', facts)

    def test_not_running_source(self):
        source = 'def danger(a):\n    __import__("os").system("exit 42")\n    return a\n'
        a = analyze_source(source)
        self.assertEqual(a[0].name, 'danger')

    def test_after_unconditional_return_is_not_reachable(self):
        source = '''def bad(a):
    return a
    if a[0] > a[1]:
        a[0], a[1] = a[1], a[0]
'''
        self.assertNotIn('element_exchange', analyze_source(source)[0].evidence)

    def test_source_parse_error_is_not_ignored(self):
        with self.assertRaises(SyntaxError):
            analyze_source('def :\n')


if __name__ == '__main__':
    unittest.main()

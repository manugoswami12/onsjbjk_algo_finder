"""v0.2 evidence tests. No candidate Python file is imported; tests use source text only."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import run_v2  # noqa: E402
from static_trace_v2 import analyze_source  # noqa: E402


def facts(source):
    return set(analyze_source(source)[0].evidence)


class V02EvidenceTests(unittest.TestCase):
    def test_v01_facts_preserved(self):
        src = (ROOT / 'examples' / 'bubble.py').read_text(encoding='utf-8')
        self.assertEqual(facts(src), {'comparison_controls_exchange', 'element_exchange',
                                      'input_sequence_mutated', 'returned_input'})

    def test_accumulator_needs_input_element(self):
        self.assertIn('input_element_accumulated', facts('def f(a):\n    s = 0\n    for x in a:\n        s += x\n    return s\n'))
        self.assertNotIn('input_element_accumulated', facts('def f(a):\n    s = 0\n    for x in a:\n        s += 2\n    return s\n'))

    def test_accumulator_must_reach_output(self):
        self.assertFalse(facts('def f(a):\n    s = 0\n    for x in a:\n        s += x\n    return 0\n'))

    def test_pair_recurrence_needs_input_driven_loop(self):
        self.assertFalse(facts('def f(n):\n    a, b = 0, 1\n    for _ in range(10):\n        a, b = b, a + b\n    return a\n'))

    def test_dead_code_gives_no_witness(self):
        self.assertFalse(facts('def f(a, b):\n    if False:\n        while b:\n            a, b = b, a % b\n    return 0\n'))

    def test_euclid_three_statement_form(self):
        self.assertIn('modulo_recurrence', facts('def f(a, b):\n    while b != 0:\n        t = a % b\n        a = b\n        b = t\n    return a\n'))

    def test_mirror_index_form(self):
        self.assertIn('mirror_compare_decides_result', facts(
            'def f(s):\n    for i in range(len(s) // 2):\n        if s[i] != s[len(s) - 1 - i]:\n            return False\n    return True\n'))

    def test_router_is_route_v2(self):
        self.assertEqual(run_v2.ROUTER.name, 'route_v2.pl')

    def test_live_launch_contract_unchanged(self):
        analyses = analyze_source('def f(a):\n    return a\n')

        def fake_run(command, **kwargs):
            self.assertEqual(command[4:8], ['-g', 'main', '-t', 'halt'])
            self.assertEqual(command[3], str(run_v2.ROUTER))
            return SimpleNamespace(returncode=0, stderr='', stdout='ROUTE f1 unknown\n')

        with patch.object(run_v2.shutil, 'which', return_value='swipl'):
            with patch.object(run_v2.subprocess, 'run', side_effect=fake_run):
                self.assertEqual(run_v2.route_live(analyses), {'f1': ['unknown']})


if __name__ == '__main__':
    unittest.main()

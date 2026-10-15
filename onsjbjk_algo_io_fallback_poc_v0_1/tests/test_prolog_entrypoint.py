"""Regression for v0.1 Windows hanging at the SWI-Prolog interactive top-level.

Uses a subprocess mock: this suite confirms the launch contract, not live
SWI-Prolog correctness. Live Prolog correctness is checked by RUN_FALLBACK_POC.cmd.
"""
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import run_poc
from static_trace import analyze_source


class PrologLaunchContract(unittest.TestCase):
    def setUp(self):
        self.analyses = analyze_source('def example(values):\n    return values\n')

    def test_explicit_main_and_noninteractive_stdin(self):
        def fake_run(command, **kwargs):
            self.assertEqual(command[:3], ['A:\\swipl\\bin\\swipl.exe', '-q', '-s'])
            self.assertEqual(command[3], str(run_poc.ROUTER))
            self.assertEqual(command[4:8], ['-g', 'main', '-t', 'halt'])
            self.assertEqual(command[8], '--')
            self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
            self.assertEqual(kwargs['timeout'], 25)
            facts = Path(command[9]).read_text(encoding='utf-8')
            self.assertIn('program(f1, anonymous).', facts)
            return SimpleNamespace(returncode=0, stderr='', stdout='ROUTE f1 unknown\n')

        with patch.object(run_poc.shutil, 'which', return_value='A:\\swipl\\bin\\swipl.exe'):
            with patch.object(run_poc.subprocess, 'run', side_effect=fake_run):
                self.assertEqual(run_poc.route_live(self.analyses), {'f1': ['unknown']})

    def test_multiple_function_facts_are_grouped_by_predicate(self):
        # Regression: original output interleaved program/2 and observed/3
        # for each function, making SWI-Prolog warn on real repo modules.
        analyses = analyze_source('''def first(a):
    return a

def second(b):
    return b

def third(c):
    return c
''')
        facts = run_poc.facts_from(analyses).splitlines()
        clauses = [line for line in facts if not line.startswith('%')]
        self.assertEqual([line for line in clauses if line.startswith('program(')], [
            'program(f1, anonymous).',
            'program(f2, anonymous).',
            'program(f3, anonymous).',
        ])
        predicate_sequence = [line.split('(', 1)[0] for line in clauses]
        self.assertEqual(predicate_sequence, sorted(predicate_sequence, reverse=True))
        self.assertEqual(sum(line.startswith('observed(') for line in clauses), 3)
        for i in range(1, 4):
            self.assertIn(f'observed(f{i}, returned_input,', '\n'.join(clauses))

    def test_multifunction_prolog_load_contract_keeps_all_functions(self):
        analyses = analyze_source('''def first(a):
    return a

def second(b):
    return b
''')
        def fake_run(command, **kwargs):
            clauses = [line for line in Path(command[9]).read_text(encoding='utf-8').splitlines()
                       if line and not line.startswith('%')]
            first_observed = next(i for i, line in enumerate(clauses)
                                  if line.startswith('observed('))
            self.assertTrue(all(line.startswith('program(')
                                for line in clauses[:first_observed]))
            self.assertTrue(all(line.startswith('observed(')
                                for line in clauses[first_observed:]))
            return SimpleNamespace(returncode=0, stderr='',
                                   stdout='ROUTE f1 unknown\nROUTE f2 unknown\n')

        with patch.object(run_poc.shutil, 'which', return_value='swipl'):
            with patch.object(run_poc.subprocess, 'run', side_effect=fake_run):
                self.assertEqual(run_poc.route_live(analyses),
                                 {'f1': ['unknown'], 'f2': ['unknown']})

    def test_multiple_functions_with_empty_evidence_still_emit_all_programs(self):
        analyses = analyze_source('''def unsupported(x):
    return external(x)

def reverse_it(a):
    for i in range(len(a) // 2):
        a[i], a[-i-1] = a[-i-1], a[i]
    return a
''')
        facts = run_poc.facts_from(analyses)
        self.assertIn('program(f1, anonymous).', facts)
        self.assertIn('program(f2, anonymous).', facts)
        self.assertNotIn('observed(f1,', facts)
        self.assertIn('observed(f2, element_exchange,', facts)
        self.assertLess(facts.index('program(f2, anonymous).'),
                        facts.index('observed(f2, element_exchange,'))

    def test_empty_prolog_output_is_error_not_success(self):
        with patch.object(run_poc.shutil, 'which', return_value='swipl'):
            with patch.object(run_poc.subprocess, 'run', return_value=SimpleNamespace(
                    returncode=0, stderr='', stdout='')):
                with self.assertRaisesRegex(RuntimeError, 'no ROUTE'):
                    run_poc.route_live(self.analyses)

    def test_timeout_has_actionable_error(self):
        with patch.object(run_poc.shutil, 'which', return_value='swipl'):
            with patch.object(run_poc.subprocess, 'run', side_effect=subprocess.TimeoutExpired('swipl', 25)):
                with self.assertRaisesRegex(RuntimeError, 'after running main'):
                    run_poc.route_live(self.analyses)

    def test_missing_swipl_rejected(self):
        with patch.object(run_poc.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'missing from PATH'):
                run_poc.route_live(self.analyses)


if __name__ == '__main__':
    unittest.main()

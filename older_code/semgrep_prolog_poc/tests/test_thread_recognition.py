"""AP6 exact-AST regression and negative controls for interleaved logic.

SWI-Prolog tests are skipped locally if it isn't installed; live Semgrep tests
are a separate gate. Synthetic fixtures must never be cited as live evidence.
"""
from __future__ import annotations
import json
import pathlib
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
from export_ast_facts import flatten
from thread_contract_ast import threaded_ast, separate_threads


def recognize_ast(ast):
    with tempfile.TemporaryDirectory() as temp:
        facts = pathlib.Path(temp) / 'facts.pl'
        facts.write_text('\n'.join(flatten(ast)) + '\n', encoding='utf-8')
        return subprocess.run([
            'swipl', '-q', '-f', 'none', '-s', str(ROOT / 'prolog' / 'thread_classify.pl'),
            '-s', str(facts), '-g', 'main_threads', '-t', 'halt'
        ], capture_output=True, text=True, timeout=55)


def recognize_live(filename):
    return subprocess.run([
        sys.executable, str(ROOT / 'tools' / 'run_demo.py'),
        '--threads', 'examples/' + filename
    ], cwd=ROOT, capture_output=True, text=True, timeout=150)


class AP6OfflineContract(unittest.TestCase):
    def test_cli_accepts_threads_and_retains_previous_flags(self):
        p = subprocess.run([sys.executable, str(ROOT/'tools'/'run_demo.py'), '--help'],
                           capture_output=True, text=True, timeout=20)
        self.assertEqual(p.returncode, 0, p.stderr)
        for flag in ('--multi', '--threads', '--ast-json'):
            self.assertIn(flag, p.stdout)

    def test_reference_exact_export_remains_unchanged(self):
        fixture = json.loads((ROOT/'tests'/'fixtures'/'semgrep_binary_ast.json').read_text())
        facts = flatten(fixture)
        self.assertEqual(len(facts), 1833)
        self.assertIn('ast_node_count(783).', facts)

    def test_direct_return_binding_regression_offline(self):
        """Structural guard for ==/2 vs =/2 when Event is initially unbound."""
        source = (ROOT / 'prolog' / 'thread_rules.pl').read_text()
        self.assertIn('Event = Statement ; under(Statement, Event)', source)
        self.assertNotIn('Statement == Event ; under(Statement, Event)', source)
        body = threaded_ast()['Pr'][1]['DefStmt'][1]['FuncDef']['fbody']['FBStmt']['Block']
        self.assertIn('Return', body[-1])
        self.assertIn('ExprStmt', body[0])

    def test_synthetic_fixture_contains_two_unmodified_threads(self):
        fixture = threaded_ast()
        facts = '\n'.join(flatten(fixture))
        for key in ("'For'", "'Mult'", "'Mod'", "'Gt'", "'ArrayAccess'", "'Tuple'"):
            self.assertIn(key, facts)
        self.assertEqual(facts.count("'Mod'"), 1)

    def test_implementation_sorts_and_returns_integer_digest(self):
        fun = runpy.run_path(str(ROOT/'examples'/'interleaved_sort_hash.py'))['inspect_items']
        data = [9, 3, 5, 0, 2]
        result = fun(data)
        self.assertEqual(data, [0, 2, 3, 5, 9])
        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 0)
        self.assertLess(result, 1000000007)

    def test_no_learning_and_existing_rules_untouched(self):
        rule = (ROOT/'prolog'/'thread_rules.pl').read_text()
        self.assertIn('polynomial_recurrence', rule)
        self.assertNotIn('set_prolog_flag(unknown, fail)',rule)
        self.assertTrue((ROOT/'prolog'/'multi_classify.pl').exists())


@unittest.skipUnless(shutil.which('swipl'), 'SWI-Prolog required')
class AP6PrologContract(unittest.TestCase):
    def recognized(self, ast):
        p = recognize_ast(ast)
        self.assertEqual(p.returncode, 0, p.stdout+'\n'+p.stderr)
        self.assertNotIn('Warning:', p.stderr)
        return p.stdout

    def test_direct_return_statement_is_discovered(self):
        """Regression: ==/2 cannot bind the direct Return event in a Block."""
        with tempfile.TemporaryDirectory() as temp:
            facts = pathlib.Path(temp) / 'facts.pl'
            facts.write_text('\n'.join(flatten(threaded_ast())) + '\n', encoding='utf-8')
            goal = ("function_definition(_,inspect_items,Body),"
                    "block_statement_holding(Body,Return,_Statement),"
                    "return_identifier(Return,digest),halt")
            p = subprocess.run([
                'swipl', '-q', '-f', 'none', '-s',
                str(ROOT / 'prolog' / 'thread_classify.pl'),
                '-s', str(facts), '-g', goal, '-t', 'halt'
            ], capture_output=True, text=True, timeout=55)
            self.assertEqual(p.returncode, 0, p.stdout+'\n'+p.stderr)
            self.assertNotIn('Warning:', p.stderr)

    def test_two_threads_and_actual_relation(self):
        text = self.recognized(threaded_ast())
        self.assertIn('CANDIDATE: bubble_sort;',text)
        self.assertIn('CANDIDATE: rolling_hash_update;',text)
        self.assertIn('RELATION: rolling_hash_update INTERLEAVED_WITH bubble_sort;',text)
        self.assertIn('state(digest)',text)

    def test_no_self_recurrence_has_no_hash(self):
        t=self.recognized(threaded_ast(old_acc='other'))
        self.assertIn('CANDIDATE: bubble_sort;',t)
        self.assertNotIn('CANDIDATE: rolling_hash_update;',t)

    def test_no_swap_retains_hash_only(self):
        t=self.recognized(threaded_ast(swap=False))
        self.assertIn('CANDIDATE: rolling_hash_update;',t)
        self.assertNotIn('CANDIDATE: bubble_sort;',t)
        self.assertNotIn('INTERLEAVED_WITH',t)

    def test_wrong_array_retains_two_but_not_relation(self):
        t=self.recognized(threaded_ast(hash_array='another'))
        self.assertIn('CANDIDATE: bubble_sort;',t)
        self.assertIn('CANDIDATE: rolling_hash_update;',t)
        self.assertNotIn('INTERLEAVED_WITH',t)

    def test_wrong_index_retains_two_but_not_relation(self):
        t=self.recognized(threaded_ast(hash_index='k'))
        self.assertIn('CANDIDATE: bubble_sort;',t)
        self.assertIn('CANDIDATE: rolling_hash_update;',t)
        self.assertNotIn('INTERLEAVED_WITH',t)

    def test_missing_return_rejects_hash(self):
        t=self.recognized(threaded_ast(include_return=False))
        self.assertNotIn('CANDIDATE: rolling_hash_update;',t)

    def test_second_accumulator_write_rejects_hash(self):
        t=self.recognized(threaded_ast(reset=True))
        self.assertNotIn('CANDIDATE: rolling_hash_update;',t)

    def test_cross_function_never_interleaved(self):
        t=self.recognized(separate_threads())
        self.assertIn('CANDIDATE: bubble_sort; function: sort_only;',t)
        self.assertIn('CANDIDATE: rolling_hash_update; function: inspect_items;',t)
        self.assertNotIn('INTERLEAVED_WITH',t)

    def test_invalid_multiplier_rejects_hash(self):
        t=self.recognized(threaded_ast(hash_multiplier=1))
        self.assertNotIn('CANDIDATE: rolling_hash_update;',t)

    def test_invalid_modulus_rejects_hash(self):
        t=self.recognized(threaded_ast(hash_modulus=5, hash_multiplier=31))
        self.assertNotIn('CANDIDATE: rolling_hash_update;',t)


@unittest.skipUnless(shutil.which('swipl') and shutil.which('semgrep'),
                     'SWI-Prolog and Semgrep required for live acceptance')
class AP6LiveWindowsAcceptance(unittest.TestCase):
    def test_actual_ocaml_ast_reports_both_threads(self):
        p=recognize_live('interleaved_sort_hash.py')
        self.assertEqual(p.returncode, 0,p.stdout+'\n'+p.stderr)
        self.assertIn('CANDIDATE: bubble_sort; function: inspect_items;',p.stdout)
        self.assertIn('CANDIDATE: rolling_hash_update; function: inspect_items;',p.stdout)
        self.assertIn('INTERLEAVED_WITH bubble_sort',p.stdout)
        self.assertNotIn('Warning:',p.stderr)

    def test_live_wrong_source_variable(self):
        p=recognize_live('interleaved_no_hash_recurrence.py')
        self.assertEqual(p.returncode, 0,p.stdout+'\n'+p.stderr)
        self.assertIn('CANDIDATE: bubble_sort;',p.stdout)
        self.assertNotIn('CANDIDATE: rolling_hash_update;',p.stdout)

    def test_live_no_swap(self):
        p=recognize_live('interleaved_no_swap.py')
        self.assertEqual(p.returncode, 0,p.stdout+'\n'+p.stderr)
        self.assertIn('CANDIDATE: rolling_hash_update;',p.stdout)
        self.assertNotIn('CANDIDATE: bubble_sort;',p.stdout)

    def test_live_wrong_array_no_interleaving(self):
        p=recognize_live('interleaved_wrong_input.py')
        self.assertEqual(p.returncode, 0,p.stdout+'\n'+p.stderr)
        self.assertIn('CANDIDATE: bubble_sort;',p.stdout)
        self.assertIn('CANDIDATE: rolling_hash_update;',p.stdout)
        self.assertNotIn('INTERLEAVED_WITH',p.stdout)

    def test_live_reset_digest_rejects_hash(self):
        p=recognize_live('interleaved_reset_digest.py')
        self.assertEqual(p.returncode, 0,p.stdout+'\n'+p.stderr)
        self.assertIn('CANDIDATE: bubble_sort;',p.stdout)
        self.assertNotIn('CANDIDATE: rolling_hash_update;',p.stdout)

    def test_live_distinct_functions_no_interleaving(self):
        p=recognize_live('interleaved_separate_functions.py')
        self.assertEqual(p.returncode, 0,p.stdout+'\n'+p.stderr)
        self.assertIn('CANDIDATE: bubble_sort; function: sort_items;',p.stdout)
        self.assertIn('CANDIDATE: rolling_hash_update; function: fingerprint;',p.stdout)
        self.assertNotIn('INTERLEAVED_WITH',p.stdout)


if __name__ == '__main__':
    unittest.main()

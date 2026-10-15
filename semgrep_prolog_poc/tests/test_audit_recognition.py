"""AP8 audit tests: source AST unchanged, strong positive/negative controls.
Synthetic mutations never substitute for the real Semgrep Windows acceptance.
"""
from __future__ import annotations
import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
from export_ast_facts import flatten
from audit_contract_ast import (CAPTURE, valid_ast, invalid_bounds, hidden_hash_update,
    premature_return, interrupted_loop, renamed_and_rebased)


def run_facts(tree):
    with tempfile.TemporaryDirectory() as tmp:
        facts = Path(tmp) / 'facts.pl'
        facts.write_text('\n'.join(flatten(tree)) + '\n', encoding='utf-8')
        return subprocess.run(['swipl','-q','-f','none','-s',str(ROOT/'prolog'/'audit_classify.pl'),
                               '-s',str(facts),'-g','main_audit','-t','halt'],
                              capture_output=True,text=True,timeout=60)


def run_live(example):
    return subprocess.run([sys.executable,str(ROOT/'tools'/'run_demo.py'),
                           '--audit', 'examples/'+example],
                          cwd=ROOT,capture_output=True,text=True,timeout=120)


class AP8OfflineTests(unittest.TestCase):
    def test_original_exporter_still_preserves_actual_ast(self):
        t = json.loads((ROOT/'tests/fixtures/semgrep_binary_ast.json').read_text())
        self.assertEqual(len(flatten(t)), 1833)
        self.assertIn('ast_node_count(783).', flatten(t))

    def test_capture_provenance_real_ast_with_wrong_accumulator(self):
        self.assertTrue(CAPTURE.is_file())
        text = CAPTURE.read_text(encoding='utf8')
        self.assertIn('"ForEach"',text)
        self.assertIn('"other"',text)

    def test_mutations_are_distinct(self):
        positive = valid_ast()
        self.assertNotEqual(positive, invalid_bounds())
        self.assertNotEqual(positive, hidden_hash_update())
        self.assertNotEqual(positive, premature_return())
        self.assertNotEqual(positive, interrupted_loop())
        self.assertNotEqual(positive, renamed_and_rebased())

    def test_python_examples_are_syntactically_valid(self):
        for name in ('audit_wrong_bounds.py','audit_dead_hash.py',
                     'audit_premature_return.py','audit_renamed.py','audit_interrupt.py'):
            with self.subTest(name=name):
                ast.parse((ROOT/'examples'/name).read_text(encoding='utf8'))

    def test_all_prior_modes_retained(self):
        p = subprocess.run([sys.executable,str(ROOT/'tools'/'run_demo.py'),'--help'],
                          capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        for option in ('--threads','--multi','--audit','--ast-json'):
            self.assertIn(option,p.stdout)

    def test_audit_has_no_external_library_dependencies(self):
        for name in ('audit_ast.pl','audit_rules.pl','audit_classify.pl'):
            self.assertTrue((ROOT/'prolog'/name).is_file())
        s = (ROOT/'prolog'/'audit_classify.pl').read_text()
        self.assertIn('recognition_audit(',s)
        self.assertIn('unverified', (ROOT/'prolog'/'audit_rules.pl').read_text())


@unittest.skipUnless(shutil.which('swipl'),'SWI-Prolog required')
class AP8PrologTests(unittest.TestCase):
    def result(self, tree):
        p = run_facts(tree)
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        self.assertNotIn('Warning:',p.stderr)
        return p.stdout

    def test_real_capture_mutated_to_valid_has_two_audited_threads(self):
        t = self.result(valid_ast())
        self.assertIn('audited_structural: bubble_sort;',t)
        self.assertIn('audited_structural: rolling_hash_update;',t)
        self.assertIn('INTERLEAVED_AUDITED:',t)

    def test_wrong_bounds_cannot_be_audited_bubble(self):
        t = self.result(invalid_bounds())
        self.assertIn('unverified: bubble_sort;',t)
        self.assertIn('audited_structural: rolling_hash_update;',t)
        self.assertNotIn('INTERLEAVED_AUDITED:',t)

    def test_guarded_hash_update_not_audited(self):
        t = self.result(hidden_hash_update())
        self.assertIn('audited_structural: bubble_sort;',t)
        self.assertNotIn('audited_structural: rolling_hash_update;',t)
        self.assertNotIn('INTERLEAVED_AUDITED:',t)

    def test_unconditional_prior_return_rejects_audits(self):
        t = self.result(premature_return())
        self.assertNotIn('audited_structural:',t)
        self.assertNotIn('INTERLEAVED_AUDITED:',t)

    def test_break_in_inner_loop_rejects_audits(self):
        t = self.result(interrupted_loop())
        self.assertNotIn('audited_structural:',t)
        self.assertNotIn('INTERLEAVED_AUDITED:',t)

    def test_renamed_variables_and_changed_base_still_audited(self):
        t = self.result(renamed_and_rebased())
        self.assertIn('audited_structural: bubble_sort; function: detect;',t)
        self.assertIn('audited_structural: rolling_hash_update; function: detect;',t)
        self.assertIn('INTERLEAVED_AUDITED:',t)

    def test_bidirectional_relational_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            facts = Path(tmp)/'facts.pl'
            facts.write_text('\n'.join(flatten(valid_ast()))+'\n',encoding='utf8')
            goal = "recognition_audit(F,A,R,audited_structural),format('~w/~w/~w~n',[F,A,R]),fail;true"
            p = subprocess.run(['swipl','-q','-f','none','-s',str(ROOT/'prolog'/'audit_classify.pl'),
                                '-s',str(facts),'-g',goal,'-t','halt'],
                               capture_output=True,text=True,timeout=60)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('inspect_items/bubble_sort/',p.stdout)
            self.assertIn('inspect_items/rolling_hash_update/',p.stdout)


@unittest.skipUnless(shutil.which('swipl') and shutil.which('semgrep'),
                     'SWI-Prolog and Semgrep required')
class AP8LiveWindowsTests(unittest.TestCase):
    def result(self, example):
        p=run_live(example)
        self.assertEqual(p.returncode,0,p.stderr+'\n'+p.stdout)
        self.assertNotIn('Warning:',p.stderr)
        return p.stdout

    def test_true_interleaving(self):
        t=self.result('interleaved_sort_hash.py')
        self.assertIn('audited_structural: bubble_sort;',t)
        self.assertIn('audited_structural: rolling_hash_update;',t)
        self.assertIn('INTERLEAVED_AUDITED:',t)

    def test_renamed_implementation(self):
        t=self.result('audit_renamed.py')
        self.assertIn('audited_structural: bubble_sort;',t)
        self.assertIn('audited_structural: rolling_hash_update;',t)
        self.assertIn('INTERLEAVED_AUDITED:',t)

    def test_misleading_loop_bounds(self):
        t=self.result('audit_wrong_bounds.py')
        self.assertNotIn('audited_structural: bubble_sort;',t)
        self.assertNotIn('INTERLEAVED_AUDITED:',t)

    def test_dead_branch_hash(self):
        t=self.result('audit_dead_hash.py')
        self.assertNotIn('audited_structural: rolling_hash_update;',t)
        self.assertNotIn('INTERLEAVED_AUDITED:',t)

    def test_unconditional_return_before_loop(self):
        t=self.result('audit_premature_return.py')
        self.assertNotIn('audited_structural:',t)

    def test_unconditional_break_inside_loop(self):
        t=self.result('audit_interrupt.py')
        self.assertNotIn('audited_structural:',t)


if __name__ == '__main__':
    unittest.main()

"""AP3 exact fact preservation and multi-hit smoke tests.

Live tests require Semgrep + SWI-Prolog; synthetic AST contracts run with SWI.
They are NOT proof that Semgrep encodes a real Python tuple swap the same way.
"""
from __future__ import annotations
import json
import runpy
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from export_ast_facts import flatten
from contract_ast import merged, separate, bubble_loop


def run_multi_ast(ast):
    with tempfile.TemporaryDirectory() as tmp:
        file = pathlib.Path(tmp)/'facts.pl'
        file.write_text('\n'.join(flatten(ast)) + '\n', encoding='utf-8')
        return subprocess.run([
            'swipl','-q','-f','none','-s',str(ROOT/'prolog'/'multi_classify.pl'),
            '-s',str(file),'-g','main_multi','-t','halt'],
            capture_output=True, text=True, timeout=40)


class ContractWithoutExternalBinaries(unittest.TestCase):
    def test_fixture_is_marked_synthetic_and_contains_real_binary(self):
        obj = merged()
        block = obj['Pr'][1]['DefStmt'][1]['FuncDef']['fbody']['FBStmt']['Block']
        self.assertIn('For', block[2])
        self.assertIn('While', block[3])
        self.assertIn('FloorDiv', json.dumps(block[3]))
        self.assertIn('Container', json.dumps(block[2]))

    def test_all_exact_json_nodes_serialized(self):
        ast = merged()
        lines = flatten(ast)
        self.assertEqual(sum(line.startswith('ast_tag(') for line in lines),
                         sum(line.startswith('ast_edge(') for line in lines)+1)
        self.assertIn("'For'", '\n'.join(lines))
        self.assertIn("'Gt'", '\n'.join(lines))
        self.assertIn("'Tuple'", '\n'.join(lines))
        self.assertIn("'While'", '\n'.join(lines))
        self.assertIn("'FloorDiv'", '\n'.join(lines))

    def test_invalid_swap_variant_differs(self):
        normal = json.dumps(bubble_loop())
        self.assertNotEqual(normal, json.dumps(bubble_loop(swap=False)))
        self.assertNotEqual(normal, json.dumps(bubble_loop(reverse=False)))
        self.assertNotEqual(normal, json.dumps(bubble_loop(compare=False)))

    def test_runner_multi_help(self):
        result = subprocess.run([sys.executable, str(ROOT/'tools'/'run_demo.py'), '--help'],
                                capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--multi', result.stdout)
        self.assertIn('--ast-json', result.stdout)

    def test_mixed_python_example_correctly_sorts_and_searches(self):
        fn = runpy.run_path(str(ROOT/'examples'/'sort_then_search.py'))['find_number']
        values = [9, 5, 2, 4, 8, 1, 0]
        index = fn(values, 5)
        self.assertEqual(values, sorted(values))
        self.assertEqual(values[index], 5)
        self.assertEqual(fn([1, 2, 3], 99), -1)

    def test_mixed_python_example_function_name_not_algorithm_name(self):
        text = (ROOT/'examples'/'sort_then_search.py').read_text(encoding='utf-8')
        self.assertIn('def find_number(', text)
        self.assertNotIn('def binary_search(', text)
        self.assertNotIn('def bubble_sort(', text)

    def test_real_semgrep_function_definition_payload_has_intermediate_record(self):
        """Protect against the exact AP4 regression: FuncDef -> record -> fbody."""
        fixture = json.loads((ROOT / 'tests' / 'fixtures' /
                             'semgrep_binary_ast.json').read_text(encoding='utf-8'))
        definition = fixture['Pr'][1]['DefStmt']
        self.assertEqual(definition[0]['name']['EN']['Id'][0][0], 'locate_item')
        funcdef = definition[1]['FuncDef']
        self.assertIn('fbody', funcdef)  # JSON record payload, NOT a FuncDef direct AST edge
        self.assertIn('Block', funcdef['fbody']['FBStmt'])
        # The exact fact exporter emits the record as a separate child via `value`.
        facts = '\n'.join(flatten(fixture))
        self.assertIn("'FuncDef'", facts)
        self.assertIn("'record'", facts)
        self.assertIn("'fbody'", facts)

    def test_legacy_ast_export_stays_the_same(self):
        fixture = json.loads((ROOT/'tests'/'fixtures'/'semgrep_binary_ast.json').read_text(encoding='utf-8'))
        lines = flatten(fixture)
        self.assertEqual(len(lines),1833)  # original AP2 report
        self.assertIn('ast_node_count(783).', lines)


@unittest.skipUnless(shutil.which('swipl'), 'SWI-Prolog not present: requires office acceptance')
class PrologRegionTests(unittest.TestCase):
    def assert_good(self, obj):
        result = run_multi_ast(obj)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('Warning:',result.stderr)
        return result.stdout

    def test_positive_both_regions_and_order(self):
        output = self.assert_good(merged())
        self.assertIn('CANDIDATE: binary_search', output)
        self.assertIn('CANDIDATE: bubble_sort', output)
        self.assertIn('RELATION: bubble_sort BEFORE binary_search', output)

    def test_missing_swap_not_recognized(self):
        output = self.assert_good(merged(swap=False))
        self.assertIn('CANDIDATE: binary_search', output)
        self.assertNotIn('CANDIDATE: bubble_sort', output)

    def test_no_reverse_assignment_is_not_swap(self):
        output = self.assert_good(merged(reverse=False))
        self.assertNotIn('CANDIDATE: bubble_sort', output)
        self.assertIn('CANDIDATE: binary_search', output)

    def test_wrong_comparison_not_bubble(self):
        output = self.assert_good(merged(compare=False))
        self.assertNotIn('CANDIDATE: bubble_sort', output)
        self.assertIn('CANDIDATE: binary_search', output)

    def test_two_functions_not_falsely_ordered(self):
        output = self.assert_good(separate())
        self.assertIn('CANDIDATE: bubble_sort; function: arrange;',output)
        self.assertIn('CANDIDATE: binary_search; function: locate_item;',output)
        self.assertNotIn('RELATION:', output)

    def test_actual_semgrep_fixture_function_discovery(self):
        """Execution test: the captured real AST must contain locate_item."""
        obj = json.loads((ROOT / 'tests' / 'fixtures' / 'semgrep_binary_ast.json').read_text())
        output = self.assert_good(obj)
        self.assertIn('function: locate_item;', output)
        self.assertNotIn('UNKNOWN: no named functions found', output)

    def test_legacy_binary_only_multi(self):
        obj = json.loads((ROOT/'tests'/'fixtures'/'semgrep_binary_ast.json').read_text())
        output = self.assert_good(obj)
        self.assertIn('CANDIDATE: binary_search', output)
        self.assertNotIn('CANDIDATE: bubble_sort',output)


@unittest.skipUnless(shutil.which('swipl') and shutil.which('semgrep'),
                     'Both Semgrep and SWI-Prolog required for live acceptance')
class LiveTwoAlgorithmTests(unittest.TestCase):
    def live(self, path):
        return subprocess.run([sys.executable, str(ROOT/'tools'/'run_demo.py'),
                               '--multi', path], capture_output=True,text=True,timeout=150)

    def test_live_same_function_both_algorithms(self):
        result=self.live('examples/sort_then_search.py')
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
        self.assertIn('CANDIDATE: bubble_sort; function: find_number;',result.stdout)
        self.assertIn('CANDIDATE: binary_search; function: find_number;',result.stdout)
        self.assertIn('RELATION: bubble_sort BEFORE binary_search',result.stdout)
        self.assertNotIn('Warning:',result.stderr)

    def test_live_sort_only(self):
        result=self.live('examples/sort_only.py')
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
        self.assertIn('CANDIDATE: bubble_sort',result.stdout)
        self.assertNotIn('CANDIDATE: binary_search',result.stdout)

    def test_live_no_swap(self):
        result=self.live('examples/no_swap_then_search.py')
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
        self.assertNotIn('CANDIDATE: bubble_sort',result.stdout)
        self.assertIn('CANDIDATE: binary_search',result.stdout)

if __name__ == '__main__':
    unittest.main()

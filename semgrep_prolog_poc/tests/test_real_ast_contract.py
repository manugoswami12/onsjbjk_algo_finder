"""Regression tests using the actual 783-node Semgrep OCaml JSON upload.

Optional SWI/semgrep tests execute on the user's Windows PC when present.
"""
from __future__ import annotations

import copy
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from export_ast_facts import flatten

FIXTURE = ROOT / 'tests' / 'fixtures' / 'semgrep_binary_ast.json'


def all_operator_values(node):
    if isinstance(node, dict):
        for key, val in node.items():
            if key == 'Op':
                yield val
            yield from all_operator_values(val)
    elif isinstance(node, list):
        for item in node:
            yield from all_operator_values(item)


def while_body(ast):
    return ast['Pr'][1]['DefStmt'][1]['FuncDef']['fbody']['FBStmt']['Block'][2]['While'][2]['Block']


def classify_ast_if_swipl(ast):
    """Exercise real SWI-Prolog against the actual exported flat facts."""
    with tempfile.TemporaryDirectory() as td:
        facts = pathlib.Path(td) / 'facts.pl'
        facts.write_text('\n'.join(flatten(ast)) + '\n', encoding='utf-8')
        command = ['swipl', '-q', '-f', 'none',
                   '-s', str(ROOT / 'prolog' / 'classify.pl'),
                   '-s', str(facts), '-g', 'main', '-t', 'halt']
        result = subprocess.run(command, text=True, capture_output=True, timeout=30)
        return result


class RealDumpStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ast = json.loads(FIXTURE.read_text(encoding='utf-8'))

    def test_real_semgrep_operator_contract(self):
        ops = list(all_operator_values(self.ast))
        self.assertTrue({'FloorDiv', 'Plus', 'Minus', 'LtE', 'Eq', 'Lt'}.issubset(set(ops)))
        self.assertEqual(len(ops), 9)
        self.assertNotIn('FloorDiv', [k for node in [self.ast] for k in node])

    def test_real_ast_export_is_preserved_without_discontiguous_clauses(self):
        lines = flatten(self.ast)
        self.assertIn('ast_node_count(783).', lines)
        predicates = [s.split('(', 1)[0] for s in lines if s.startswith('ast_')]
        # Each predicate occupies one contiguous block (no SWI warning).
        transitions = [p for index, p in enumerate(predicates) if index == 0 or p != predicates[index-1]]
        self.assertEqual(transitions,
                         ['ast_edge', 'ast_tag', 'ast_scalar', 'ast_node_count'])
        self.assertIn("'FloorDiv'", '\n'.join(lines))
        self.assertIn("'locate_item'", '\n'.join(lines))

    def test_real_positive_structure_has_consistent_variables(self):
        # Inspect OCaml AST JSON only. This is a preflight for the Prolog
        # fixture, not a substitute for the optional SWI-Prolog test.
        def name(expr):
            return expr['N']['Id'][0][0]
        statements = self.ast['Pr'][1]['DefStmt'][1]['FuncDef']['fbody']['FBStmt']['Block']
        while_node = statements[2]['While']
        cond = while_node[1]['Cond']['Call']
        self.assertEqual(cond[0]['Special'][0]['Op'], 'LtE')
        low = name(cond[1][0]['Arg'])
        high = name(cond[1][1]['Arg'])
        body = while_node[2]['Block']
        midpoint = body[0]['ExprStmt'][0]['Assign']
        mid = name(midpoint[0])
        plus_args = midpoint[2]['Call'][1][0]['Arg']['Call'][1]
        self.assertEqual([name(arg['Arg']) for arg in plus_args], [low, high])
        match = body[1]['If']
        equal_call = match[1]['Cond']['Call']
        self.assertEqual(equal_call[0]['Special'][0]['Op'], 'Eq')
        indexed = equal_call[1][0]['Arg']['ArrayAccess']
        self.assertEqual(name(indexed[1]), mid)
        returned = match[2]['Block'][0]['Return'][1]['some']
        self.assertEqual(name(returned), mid)
        narrow = body[2]['If']
        self.assertEqual(name(narrow[2]['Block'][0]['ExprStmt'][0]['Assign'][0]), low)
        self.assertEqual(name(narrow[3]['some']['Block'][0]['ExprStmt'][0]['Assign'][0]), high)

    def test_operator_encoding_within_actual_while_body(self):
        body = while_body(self.ast)
        midpoint = body[0]['ExprStmt'][0]['Assign'][2]
        self.assertEqual(midpoint['Call'][0]['Special'][0]['Op'], 'FloorDiv')
        plus = midpoint['Call'][1][0]['Arg']
        self.assertEqual(plus['Call'][0]['Special'][0]['Op'], 'Plus')
        two = midpoint['Call'][1][1]['Arg']['L']['Int'][0]['some']
        self.assertEqual(two, 2)


@unittest.skipUnless(shutil.which('swipl'), 'SWI-Prolog not installed in this runtime')
class RealPrologRecognitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ast = json.loads(FIXTURE.read_text(encoding='utf-8'))

    def assert_candidate(self, ast, expected):
        result = classify_ast_if_swipl(ast)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('discontiguous', result.stderr.lower(), result.stderr[:1000])
        self.assertIn('AST nodes exported:', result.stdout)
        self.assertIn(expected, result.stdout)
        return result

    def test_real_binary_search_positive(self):
        self.assert_candidate(self.ast, 'CANDIDATE: binary_search')

    def test_mutation_changed_midpoint_division_unknown(self):
        bad = copy.deepcopy(self.ast)
        midpoint = while_body(bad)[0]['ExprStmt'][0]['Assign'][2]
        midpoint['Call'][0]['Special'][0]['Op'] = 'Div'
        self.assert_candidate(bad, 'UNKNOWN: no algorithm signature matched')

    def test_mutation_changed_interval_guard_unknown(self):
        bad = copy.deepcopy(self.ast)
        guard = bad['Pr'][1]['DefStmt'][1]['FuncDef']['fbody']['FBStmt']['Block'][2]['While'][1]['Cond']
        guard['Call'][0]['Special'][0]['Op'] = 'Lt'
        self.assert_candidate(bad, 'UNKNOWN: no algorithm signature matched')

    def test_mutation_wrong_upper_update_variable_unknown(self):
        bad = copy.deepcopy(self.ast)
        else_block = while_body(bad)[2]['If'][3]['some']['Block']
        rhs = else_block[0]['ExprStmt'][0]['Assign'][2]
        index = rhs['Call'][1][0]['Arg']['N']['Id'][0]
        index[0] = 'some_other_variable'
        self.assert_candidate(bad, 'UNKNOWN: no algorithm signature matched')

    def test_positive_variable_rename(self):
        changed = copy.deepcopy(self.ast)
        def walk(node):
            if isinstance(node, dict):
                if 'Id' in node and isinstance(node['Id'], list):
                    namepart = node['Id'][0]
                    if isinstance(namepart, list) and namepart[0] in {'lower', 'upper', 'pivot'}:
                        namepart[0] = {'lower':'left', 'upper':'right', 'pivot':'middle'}[namepart[0]]
                for val in node.values():
                    walk(val)
            elif isinstance(node, list):
                for val in node:
                    walk(val)
        walk(changed)
        output = self.assert_candidate(changed, 'CANDIDATE: binary_search')
        self.assertIn('left', output.stdout)
        self.assertIn('middle', output.stdout)


@unittest.skipUnless(shutil.which('semgrep') and shutil.which('swipl'),
                     'Full Semgrep and SWI-Prolog tools not installed in this runtime')
class LiveSemgrepEndToEndTests(unittest.TestCase):
    def test_real_binary_source(self):
        cmd = [sys.executable, str(ROOT / 'tools' / 'run_demo.py'),
               'examples/search_binary.py']
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=140)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CANDIDATE: binary_search', result.stdout)

    def test_real_linear_source(self):
        cmd = [sys.executable, str(ROOT / 'tools' / 'run_demo.py'),
               'examples/search_linear.py']
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=140)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('UNKNOWN: no algorithm signature matched', result.stdout)


if __name__ == '__main__':
    unittest.main()

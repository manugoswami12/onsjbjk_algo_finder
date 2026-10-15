"""AP9 baseline-preservation and deterministic reference matching checks."""
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
from typed_ast_codec import (JsonNumber, decode_typed, json_text, strict_load,
                             strict_loads, typed_lines)
from reference_pattern import (references, candidates, compile_reference,
                               compile_candidates, functions, REGIONS)
from evaluate_reference import evaluate, detect_oracle

CASES = ROOT/'tests/fixtures/ap9_cases'


class TypedExactness(unittest.TestCase):
    def test_every_json_scalar_type_remains_distinct(self):
        content = '{"stringFalse":"false","boolFalse":false,"strTwo":"2", "numTwo":2,' \
                  '"nullString":"null","realNull":null,"exponent":1e+2,"negzero":-0}'
        original = strict_loads(content)
        recovered = decode_typed(typed_lines(original))
        self.assertEqual(json_text(original), json_text(recovered))
        self.assertEqual(recovered['boolFalse'], False)
        self.assertIs(recovered['realNull'], None)
        self.assertIs(type(recovered['numTwo']), JsonNumber)
        self.assertEqual(recovered['exponent'], JsonNumber('1e+2'))
        self.assertEqual(recovered['negzero'], JsonNumber('-0'))
        self.assertIs(type(recovered['stringFalse']), str)

    def test_empty_object_and_array_distinguished(self):
        obj = strict_loads('{"a":{},"b":[],"record":{"value":"x"}}')
        self.assertEqual(json_text(obj), json_text(decode_typed(typed_lines(obj))))

    def test_one_key_record_and_nested_unicode_roundtrip(self):
        obj = strict_loads('{"\\ud800": "\\udfff", "quote\\\"": ["line\\n", "\\u00e9", 2.300e-12]}')
        self.assertEqual(json_text(obj), json_text(decode_typed(typed_lines(obj))))

    def test_duplicates_rejected_not_silently_dropped(self):
        for raw in ('{"x":1,"x":2}', '{"n":{"x":true,"x":false}}'):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, 'duplicate'):
                strict_loads(raw)

    def test_nan_infinity_rejected(self):
        for raw in ('NaN','Infinity','-Infinity'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                strict_loads(raw)

    def test_original_ap8_exporter_byte_contract_preserved(self):
        fixture = ROOT/'tests/fixtures/semgrep_binary_ast.json'
        tree = json.loads(fixture.read_text(encoding='utf8'))
        self.assertEqual(len(flatten(tree)), 1833)
        self.assertNotIn('ast_json_type', '\n'.join(flatten(tree)))
        self.assertEqual(json_text(strict_load(fixture)),
                         json_text(decode_typed(typed_lines(strict_load(fixture)))))

    def test_bounded_export(self):
        with self.assertRaises(ValueError):
            typed_lines([1,2,3], max_nodes=2)

    def test_cli_lossless_replay(self):
        with tempfile.TemporaryDirectory() as td:
            inp = CASES/'binary_exact.json'
            out = pathlib.Path(td)/'facts.pl'
            p = subprocess.run([sys.executable, str(ROOT/'tools/typed_ast_codec.py'),
                                str(inp), str(out), '--verify-roundtrip'],
                               text=True,capture_output=True,timeout=25)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('ast_json_type',out.read_text())


class ReferenceContract(unittest.TestCase):
    def test_function_discovery_real_capture(self):
        t = strict_load(CASES/'binary_exact.json')
        self.assertEqual([n for _,n,_,_ in functions(t)], ['locate_item'])

    def test_generated_code_contains_pattern_and_genuine_logic(self):
        t = strict_load(CASES/'binary_exact.json')
        clause, meta = references(t,'user_label','locate_item','body',0)
        self.assertIn('reference_pattern(',clause)
        self.assertIn('binding(V0)',clause)
        self.assertIn("'LtE'",clause)
        self.assertNotIn("'id_info_id'",clause)
        self.assertEqual(meta['local_slots'][0], 'lower')
        self.assertEqual(meta['label'], 'user_label')

    def test_generated_label_does_not_change_matching(self):
        t = strict_load(CASES/'binary_exact.json')
        a, _ = references(t,'label_a','locate_item','body',0)
        b, _ = references(t,'other_label','locate_item','body',0)
        self.assertEqual(a.replace("'label_a'", "'x'"),
                         b.replace("'other_label'", "'x'"))

    def test_renaming_is_allowed_but_operator_constant_global_not(self):
        reference = strict_load(CASES/'binary_exact.json')
        expected = {
            'binary_exact': {'locate_item'},
            'binary_renamed': {'renamed_search'},
            'binary_bad_operator': set(),
            'binary_bad_literal': set(),
            'binary_bad_builtin': set(),
            'binary_conflated_names': set(),
        }
        for file, names in expected.items():
            with self.subTest(file=file):
                result = detect_oracle(reference,'locate_item','body',0,
                                       strict_load(CASES/(file+'.json')))
                self.assertEqual(result, names)

    def test_interleaved_hash_exactness_and_renaming(self):
        reference = strict_load(CASES/'sort_hash_reference.json')
        expected = {
            'sort_hash_reference': {'inspect_items'},
            'sort_hash_renamed': {'blend'},
            'sort_hash_wrong_bounds': set(),
            'sort_hash_wrong_state': set(),
        }
        for file, names in expected.items():
            with self.subTest(file=file):
                self.assertEqual(detect_oracle(reference,'inspect_items','body',0,
                                    strict_load(CASES/(file+'.json'))), names)

    def test_region_selection_for_is_different_from_whole_body(self):
        t = strict_load(CASES/'sort_hash_reference.json')
        b, _ = references(t,'sort_hash','inspect_items','body',0)
        loop, _ = references(t,'sort_hash','inspect_items','for',0)
        self.assertNotEqual(b, loop)
        self.assertIn("'For'",loop)

    def test_source_not_hardcoded_in_pattern_runner(self):
        src = (ROOT/'tools/reference_pattern.py').read_text()
        self.assertNotIn('binary_search_ref',src)
        self.assertNotIn('sort_hash_ref',src)
        self.assertNotIn('inspect_items',src)

    def test_prolog_generation_is_repeatable(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = pathlib.Path(td)/'a.pl',pathlib.Path(td)/'b.pl'
            source = CASES/'binary_exact.json'
            compile_reference(source, 'algorithm_name', 'locate_item', 'body',0,a)
            compile_reference(source, 'algorithm_name', 'locate_item', 'body',0,b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            compile_candidates(source, REGIONS, b)
            self.assertIn('candidate_pattern(',b.read_text())

    def test_offline_dataset_confusion_counts(self):
        result = evaluate(CASES/'manifest.json',backend='python_oracle')
        self.assertTrue(result['all_expected_results_match'])
        self.assertEqual(result['counts'],dict(TP=4, FP=0, FN=0, TN=16))
        self.assertIn('bounded',result['disclaimer'])

    def test_user_facing_runner_offline(self):
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run([sys.executable,str(ROOT/'tools/run_reference.py'),
                                str(CASES/'binary_exact.json'),str(CASES/'binary_renamed.json'),
                                '--label','search_signature','--function','locate_item',
                                '--region','body','--out-dir',td,'--offline-only'],
                               text=True,capture_output=True,timeout=25)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('JSON_VALUE_ROUNDTRIP: PASS',p.stdout)
            self.assertIn('Prolog recognition NOT RUN',p.stdout)


@unittest.skipUnless(shutil.which('swipl'), 'SWI-Prolog unavailable')
class ReferenceRealPrologTests(unittest.TestCase):
    def match(self, ref, target, label, function, region='body'):
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run([sys.executable,str(ROOT/'tools/run_reference.py'),
                 str(CASES/(ref+'.json')),str(CASES/(target+'.json')),
                 '--label',label,'--function',function,'--region',region,'--out-dir',td],
                capture_output=True,text=True,timeout=120)
            self.assertEqual(p.returncode,0,p.stderr+'\n'+p.stdout)
            self.assertNotIn('Warning:',p.stderr)
            return p.stdout

    def test_live_unification_with_renamed_variables(self):
        self.assertIn('REFERENCE_STRUCTURAL_MATCH:',
                      self.match('binary_exact','binary_renamed','unfamiliar_name','locate_item'))

    def test_live_unification_rejects_changed_builtin(self):
        self.assertIn('UNKNOWN: no reference structural match',
                      self.match('binary_exact','binary_bad_builtin','unknown_label','locate_item'))

    def test_live_distinct_binding_requirement(self):
        self.assertIn('UNKNOWN: no reference structural match',
                      self.match('binary_exact','binary_conflated_names','unfamiliar_name','locate_item'))

    def test_real_prolog_evaluation(self):
        result = evaluate(CASES/'manifest.json',backend='prolog')
        self.assertTrue(result['all_expected_results_match'], result)
        self.assertEqual(result['counts'],dict(TP=4, FP=0, FN=0, TN=16))


@unittest.skipUnless(shutil.which('semgrep') and shutil.which('swipl'),
                     'Real Semgrep + SWI-Prolog required')
class RealPythonSourceTests(unittest.TestCase):
    def test_source_to_generated_prolog_pipeline(self):
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run([sys.executable,str(ROOT/'tools/run_reference.py'),
                str(ROOT/'examples/search_binary.py'),str(ROOT/'examples/search_binary.py'),
                '--label','author_assigned_label','--function','locate_item',
                '--region','body','--out-dir',td], capture_output=True,text=True,timeout=140)
            self.assertEqual(p.returncode,0,p.stderr+'\n'+p.stdout)
            self.assertIn('REFERENCE_STRUCTURAL_MATCH:',p.stdout)

if __name__=='__main__':
    unittest.main()

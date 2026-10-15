"""AP10 conformance oracle + actual SWI tests when available.

The oracle models the tightly scoped 'Block subsequence' matching contract;
recognition itself lives in Prolog. Windows acceptance rejects absent SWI/Semgrep.
"""
import copy
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from reference_pattern import Binding, compile_candidates, compile_reference, declared_names, functions, project_region
from typed_ast_codec import strict_load, json_text
from ap10_reference_bundle import bundle_references

DATA = ROOT / 'tests' / 'fixtures' / 'ap10'
AP9_DATA = ROOT / 'tests' / 'fixtures' / 'ap9_cases'


def oracle(reference, target, state=None):
    """Pure functional exhaustive check, no editing source or generated patterns."""
    state = ({}, {}) if state is None else state
    forward, backward = state
    if isinstance(reference, Binding):
        if not isinstance(target, Binding): return None
        if reference.name in forward:
            return state if forward[reference.name] == target.name else None
        if target.name in backward: return None
        return (forward | {reference.name: target.name},
                backward | {target.name: reference.name})
    if type(reference) is not type(target): return None
    if isinstance(reference, dict):
        if list(reference) != list(target): return None
        if list(reference) == ['Block'] and isinstance(reference['Block'], list):
            needles, haystack = reference['Block'], target['Block']
            def search(i, j, mapping):
                if i == len(needles): return mapping
                for k in range(j, len(haystack)):
                    next_mapping = oracle(needles[i], haystack[k], mapping)
                    if next_mapping is not None:
                        finished = search(i + 1, k + 1, next_mapping)
                        if finished is not None: return finished
                return None
            return search(0, 0, state)
        for key in reference:
            state = oracle(reference[key], target[key], state)
            if state is None:return None
        return state
    if isinstance(reference, list):
        if len(reference) != len(target):return None
        for r, t in zip(reference, target):
            state = oracle(r, t, state)
            if state is None:return None
        return state
    return state if reference == target else None


def body(tree):
    result = []
    for _, name, params, statements in functions(tree):
        result.append((name, project_region({'Block': statements},
                                            declared_names(params, statements))))
    return result


class AP10Contract(unittest.TestCase):
    def test_reference_threads_match_mixed_and_renamed(self):
        sort_ref = body(strict_load(DATA / 'sort_reference.json'))[0][1]
        hash_ref = body(strict_load(DATA / 'hash_reference.json'))[0][1]
        for name in ('sort_hash_reference', 'sort_hash_renamed'):
            with self.subTest(name=name):
                target = body(strict_load(AP9_DATA / (name + '.json')))[0][1]
                self.assertIsNotNone(oracle(sort_ref, target))
                self.assertIsNotNone(oracle(hash_ref, target))

    def test_contradictions_do_not_spread_across_threads(self):
        sort_ref = body(strict_load(DATA / 'sort_reference.json'))[0][1]
        hash_ref = body(strict_load(DATA / 'hash_reference.json'))[0][1]
        broken = body(strict_load(AP9_DATA / 'sort_hash_wrong_state.json'))[0][1]
        self.assertIsNotNone(oracle(sort_ref, broken))
        self.assertIsNone(oracle(hash_ref, broken))
        bounds = body(strict_load(AP9_DATA / 'sort_hash_wrong_bounds.json'))[0][1]
        self.assertIsNone(oracle(sort_ref, bounds))
        self.assertIsNone(oracle(hash_ref, bounds))

    def test_extra_inner_loop_statements_do_not_break_threads(self):
        target = body(strict_load(DATA / 'interleaved_with_extra.json'))[0][1]
        for reference in ('sort_reference', 'hash_reference'):
            with self.subTest(reference=reference):
                expected = body(strict_load(DATA / (reference + '.json')))[0][1]
                self.assertIsNotNone(oracle(expected, target))

    def test_different_function_threads_remain_separate(self):
        candidates = dict(body(strict_load(DATA / 'separate_functions.json')))
        sort = body(strict_load(DATA / 'sort_reference.json'))[0][1]
        digest = body(strict_load(DATA / 'hash_reference.json'))[0][1]
        self.assertEqual(set(candidates), {'sort_out', 'hash_out'})
        self.assertIsNotNone(oracle(sort, candidates['sort_out']))
        self.assertIsNotNone(oracle(digest, candidates['hash_out']))
        self.assertIsNone(oracle(digest, candidates['sort_out']))
        self.assertIsNone(oracle(sort, candidates['hash_out']))

    def test_reversed_required_statements_does_not_match(self):
        src = strict_load(DATA / 'hash_reference.json')
        ref = body(src)[0][1]
        changed = copy.deepcopy(src)
        item = next(functions(changed))
        item[3].reverse()
        self.assertIsNone(oracle(ref, body(changed)[0][1]))

    def test_catalog_does_not_hardcode_algorithm_names(self):
        code = (ROOT / 'prolog' / 'ap10_threads.pl').read_text(encoding='utf-8')
        self.assertNotIn('bubble_sort', code)
        self.assertNotIn('rolling_hash', code)
        code = (ROOT / 'tools' / 'ap10_cli.py').read_text(encoding='utf-8')
        self.assertNotIn('bubble_sort', code)
        self.assertNotIn('rolling_hash', code)

    def test_current_ap9_generator_compiles_both_refs(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in ('sort_reference', 'hash_reference'):
                p = pathlib.Path(temp) / (name + '.pl')
                result = compile_reference(DATA / (name + '.json'), name,
                                           'inspect_items', 'body', 0, p)
                self.assertIn('label', result)
                self.assertIn('reference_pattern(', p.read_text())

    def test_bundle_preserves_generated_sources_and_two_clauses(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            originals = {}
            for name in ('sort', 'hash'):
                dest = base / (name + '.pl')
                compile_reference(DATA / (name + '_reference.json'), name,
                                  'inspect_items', 'body', 0, dest)
                originals[name] = dest.read_bytes()
            bundle = bundle_references([('sort', base / 'sort.pl'),
                                        ('hash', base / 'hash.pl')],
                                       base / 'all_references.pl')
            content = bundle.read_text(encoding='utf-8')
            self.assertEqual(content.count('reference_pattern('), 2)
            self.assertIn("reference_pattern('sort',", content)
            self.assertIn("reference_pattern('hash',", content)
            for label, original in originals.items():
                self.assertEqual(original, (base / (label + '.pl')).read_bytes())

    def test_bundle_rejects_duplicate_labels_and_untrusted_directives(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            ref = base / 'sort.pl'
            compile_reference(DATA / 'sort_reference.json', 'sort',
                              'inspect_items', 'body', 0, ref)
            with self.assertRaisesRegex(ValueError, 'duplicate reference label'):
                bundle_references([('sort', ref), ('sort', ref)], base / 'dupes.pl')
            with self.assertRaisesRegex(ValueError, 'not a single AP9-generated'):
                bundle_references([('hash', ref)], base / 'mismatch.pl')
            with ref.open('a', encoding='utf-8') as stream:
                stream.write(':- halt.\n')
            with self.assertRaisesRegex(ValueError, 'not a single AP9-generated'):
                bundle_references([('sort', ref)], base / 'inject.pl')

    def test_cli_scan_consults_single_bundle_for_multiple_algorithms(self):
        from ap10_cli import learn, scan
        with tempfile.TemporaryDirectory() as tmp:
            store = pathlib.Path(tmp)
            learn(store, 'sort', DATA / 'sort_reference.json', 'inspect_items', 0)
            learn(store, 'hash', DATA / 'hash_reference.json', 'inspect_items', 0)
            with patch('ap10_cli.shutil.which', return_value='mock-swipl'), \
                 patch('ap10_cli.subprocess.run') as prolog:
                prolog.return_value.returncode = 0
                prolog.return_value.stdout = ''
                prolog.return_value.stderr = ''
                self.assertEqual(scan(store, DATA / 'interleaved_with_extra.json'), 0)
                argv = prolog.call_args.args[0]
                self.assertIn(str(store / 'all_references.pl'), argv)
                self.assertNotIn(str(store / 'sort.pl'), argv)
                self.assertNotIn(str(store / 'hash.pl'), argv)
                self.assertEqual(sum(line.startswith('reference_pattern(')
                                     for line in (store / 'all_references.pl').read_text(
                                         encoding='utf-8').splitlines()), 2)

    def test_cli_learn_catalog_is_persistent_and_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [sys.executable, str(ROOT / 'tools' / 'ap10_cli.py'), '--store', tmp,
                   'learn', 'reference_one', str(DATA / 'sort_reference.json'), 'inspect_items']
            first = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            self.assertEqual(second.returncode, 2)
            self.assertIn('already exists', second.stderr)
            self.assertTrue((pathlib.Path(tmp) / 'reference_one.pl').exists())


@unittest.skipUnless(shutil.which('swipl'), 'SWI-Prolog unavailable; run on Windows')
class AP10LiveSWI(unittest.TestCase):
    def run_match(self, target):
        return self.run_match_fixture(AP9_DATA / (target + '.json'))

    def run_match_fixture(self, target_path):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            for name in ('sort', 'hash'):
                compile_reference(DATA / (('sort' if name == 'sort' else 'hash') + '_reference.json'),
                                  name, 'inspect_items', 'body', 0, base / (name + '.pl'))
            compile_candidates(target_path, ('body',), base / 'target.pl')
            bundled = bundle_references([('sort', base / 'sort.pl'),
                                         ('hash', base / 'hash.pl')],
                                        base / 'all_references.pl')
            call = ['swipl', '-q', '-f', 'none',
                    '-s', str(ROOT / 'prolog' / 'reference_match.pl'),
                    '-s', str(ROOT / 'prolog' / 'ap10_threads.pl'),
                    '-s', str(bundled),
                    '-s', str(base / 'target.pl'), '-g', 'main_ap10', '-t', 'halt']
            p = subprocess.run(call, capture_output=True, text=True, timeout=90)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertNotIn('Warning:', p.stderr)
            return p.stdout

    def test_two_threads_share_real_loop(self):
        txt = self.run_match('sort_hash_reference')
        self.assertIn('AP10_THREAD: sort;', txt)
        self.assertIn('AP10_THREAD: hash;', txt)
        self.assertIn('relation: shared_loop', txt)

    def test_variable_renaming_survives(self):
        txt = self.run_match('sort_hash_renamed')
        self.assertIn('AP10_THREAD: sort;', txt)
        self.assertIn('AP10_THREAD: hash;', txt)

    def test_wrong_accumulator_does_not_damage_sort(self):
        txt = self.run_match('sort_hash_wrong_state')
        self.assertIn('AP10_THREAD: sort;', txt)
        self.assertNotIn('AP10_THREAD: hash;', txt)

    def test_interleaved_with_unrelated_statement(self):
        txt = self.run_match_fixture(DATA / 'interleaved_with_extra.json')
        self.assertIn('AP10_THREAD: sort;', txt)
        self.assertIn('AP10_THREAD: hash;', txt)
        self.assertIn('relation: shared_loop', txt)

    def test_separate_functions_never_composed(self):
        txt = self.run_match_fixture(DATA / 'separate_functions.json')
        self.assertIn('AP10_THREAD: sort;', txt)
        self.assertIn('AP10_THREAD: hash;', txt)
        self.assertNotIn('AP10_RELATION:', txt)

    def test_wrong_bounds_rejected(self):
        txt = self.run_match('sort_hash_wrong_bounds')
        self.assertIn('UNKNOWN:', txt)


if __name__ == '__main__':
    unittest.main()

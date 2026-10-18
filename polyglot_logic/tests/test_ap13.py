"""AP13 tests (stdlib unittest). Tiers:
1. offline: tables, term rendering, Haskell fixity, store, CLI errors (no tools needed)
2. lowering: tree-sitter facts (skipped without tree-sitter-language-pack)
3. live acceptance A1-A7 of doc 01 (skipped without SWI-Prolog and tree-sitter)
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
TOOLS = ROOT / 'tools'
CLI = TOOLS / 'cli.py'
EX = ROOT / 'examples'
POC = REPO / 'older_code' / 'onsjbjk_algo_io_fallback_poc_v0_1' / 'examples'
sys.path.insert(0, str(TOOLS))

import fact_io  # noqa: E402
import knowledge_store  # noqa: E402
import lang_tables  # noqa: E402
from lower_equations import shunting_yard  # noqa: E402

HAVE_TS = importlib.util.find_spec('tree_sitter_language_pack') is not None
HAVE_SWIPL = shutil.which('swipl') is not None
LANG_FILES = {
    'bubble': ['bubble.py', 'bubble.rs', 'Bubble.java', 'bubble.c', 'bubble.R', 'bubble.hs',
               'bubble.lisp', 'bubble.pl'],
    'binary_search': ['binary_search.py', 'binary_search.rs', 'BinarySearch.java', 'binary_search.c',
                      'binary_search.R', 'binary_search.hs', 'binary_search.lisp', 'binary_search.pl'],
}
# A1: the frozen AP12 POC's own expected routes (onsjbjk_algo_io_fallback_poc_v0_1/run_poc.py)
POC_ROUTES = {
    'bubble.py': {'comparison_driven_reordering', 'sequence_rearrangement'},
    'reverse.py': {'sequence_rearrangement'},
    'binary.py': {'indexed_lookup', 'interval_lookup'},
    'linear.py': {'indexed_lookup'},
    'unrelated_compare.py': {'unknown'},
    'unrelated_array.py': {'sequence_rearrangement'},
    'fake_midpoint.py': {'unknown'},
    'dead_swap.py': {'unknown'},
    'wrong_exchange.py': {'unknown'},
    'mixed.py': {'comparison_driven_reordering', 'indexed_lookup', 'interval_lookup',
                 'sequence_rearrangement'},
    'unknown_call.py': {'unknown'},
}


def cli(*args, env=None):
    return subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True,
                          timeout=300, env=env)


class OfflineTests(unittest.TestCase):
    def test_every_language_has_an_extension(self):
        self.assertEqual(set(lang_tables.EXTENSIONS.values()), set(lang_tables.LANGUAGES))

    def test_term_rendering_quotes_atoms(self):
        t = fact_io.op('gt', fact_io.elem(fact_io.var("it's"), fact_io.var('j')), fact_io.num(1))
        self.assertEqual(fact_io.term(t), "'op'('gt',['elem'('var'('it\\'s'),'var'('j')),1])"
                         .replace(",1])", ",'int'(1)])"))

    def test_haskell_fixity_rebuilds_index_then_equality(self):
        # a ! mid == target   (tree-sitter: flat chain) -> (a ! mid) == target
        tree = shunting_yard(['a', ('OP', '!'), 'mid', ('OP', '=='), 'target'])
        self.assertEqual(tree, ('bin', '==', ('bin', '!', 'a', 'mid'), 'target'))

    def test_haskell_cons_is_right_associative(self):
        tree = shunting_yard(['x', ('OP', ':'), 'y', ('OP', ':'), 'rest'])
        self.assertEqual(tree, ('bin', ':', 'x', ('bin', ':', 'y', 'rest')))

    def test_store_is_immutable_and_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td)
            row = dict(label='l1', language='python', source_path='x.py', function_name='f',
                       branch='unknown', relations=1, origin='file', ap11_label='', category='')
            self.assertEqual(knowledge_store.save(store, row, 'reference(l1,unknown,[],[]).\n'), 'generated')
            self.assertEqual(knowledge_store.save(store, row, 'reference(l1,unknown,[],[]).\n'),
                             'already_present')
            with self.assertRaises(ValueError):
                knowledge_store.save(store, row, 'reference(l1,unknown,[x],[]).\n')
            self.assertEqual(len(knowledge_store.reference_files(store, True)), 1)
            self.assertEqual(len(knowledge_store.reference_files(store, False)), 0)
            knowledge_store.approve(store, 'l1', 'approved')
            self.assertEqual(len(knowledge_store.reference_files(store, False)), 1)
            (store / 'patterns' / 'l1.pl').write_text('tampered', encoding='utf-8')
            with self.assertRaises(ValueError):
                knowledge_store.reference_files(store, True)

    def test_missing_source_is_an_error_not_unknown(self):
        r = cli('scan', ROOT / 'no_such_file.py')
        self.assertEqual(r.returncode, 2)
        self.assertIn('source not found', r.stderr)

    def test_unsupported_extension_is_an_error(self):
        r = cli('facts', ROOT / 'docs' / '01_AP13_REQUIREMENTS_DESIGN.md')
        self.assertEqual(r.returncode, 2)
        self.assertIn('unsupported source extension', r.stderr)

    def test_frozen_router_is_present_and_unmodified_by_ap13(self):
        router = REPO / 'older_code' / 'algo_reference_corpus' / 'ap12' / 'prolog' / 'route_extended.pl'
        self.assertTrue(router.is_file())
        self.assertIn('route(F, interval_lookup)', router.read_text(encoding='utf-8'))


@unittest.skipUnless(HAVE_TS, 'tree-sitter-language-pack not installed')
class LoweringTests(unittest.TestCase):
    def facts(self, path):
        from cli import facts_text
        return facts_text(path)[1]

    def test_five_imperative_languages_give_identical_binary_search_logic(self):
        wanted = ["'op'('div',['op'('add',['var'('low'),'var'('high')]),'int'(2)])",
                  "'op'('add',['var'('mid'),'int'(1)])", "'op'('sub',['var'('mid'),'int'(1)])",
                  "loop_cond("]
        for name in ['binary_search.py', 'binary_search.rs', 'BinarySearch.java', 'binary_search.c',
                     'binary_search.R', 'binary_search.lisp']:
            text = self.facts(EX / 'binary_search' / name)
            for w in wanted:
                self.assertIn(w, text, name)

    def test_haskell_pass_becomes_a_positional_exchange(self):
        text = self.facts(EX / 'bubble' / 'bubble.hs')
        self.assertIn("par_assign(", text)
        self.assertIn("loop_var(", text)
        self.assertIn("'$cursor'", text)

    def test_dead_branch_is_not_live(self):
        text = self.facts(POC / 'dead_swap.py')
        self.assertNotIn('par_assign(', text)


@unittest.skipUnless(HAVE_TS and HAVE_SWIPL, 'needs tree-sitter-language-pack and swipl')
class LiveAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory(prefix='ap13_test_')
        cls.store = Path(cls.td.name) / 'store'
        for label, src, fn in (('ref_bubble_py', EX / 'bubble' / 'bubble.py', 'bubble_sort'),
                               ('ref_binary_py', EX / 'binary_search' / 'binary_search.py', 'binary_search')):
            r = cli('--store', cls.store, 'learn', label, src, fn)
            assert r.returncode == 0, r.stderr

    @classmethod
    def tearDownClass(cls):
        cls.td.cleanup()

    def scan(self, path):
        sys.path.insert(0, str(TOOLS))
        from cli import scan
        return scan(path, self.store, True, quiet=True)

    def routes(self, result):
        return set().union(*(set(f['routes']) for f in result['functions']))

    def leaf_matches(self, result):
        return {x['label'] for x in result['leaves'] if x['result'] == 'MATCH'}

    def test_A1_poc_routes_reproduced_from_tree_sitter_facts(self):
        for name, expected in POC_ROUTES.items():
            result = self.scan(POC / name)
            self.assertEqual(len(result['functions']), 1, name)
            self.assertEqual(set(result['functions'][0]['routes']), expected, name)

    def test_A2_bubble_learned_from_python_matches_eight_languages(self):
        for name in LANG_FILES['bubble']:
            result = self.scan(EX / 'bubble' / name)
            self.assertIn('comparison_driven_reordering', self.routes(result), name)
            self.assertEqual(self.leaf_matches(result), {'ref_bubble_py'}, name)

    def test_A3_binary_search_learned_from_python_matches_eight_languages(self):
        for name in LANG_FILES['binary_search']:
            result = self.scan(EX / 'binary_search' / name)
            self.assertIn('interval_lookup', self.routes(result), name)
            self.assertEqual(self.leaf_matches(result), {'ref_binary_py'}, name)

    def test_A4_negatives_never_leaf_match(self):
        for path in sorted((EX / 'negative').iterdir()):
            result = self.scan(path)
            self.assertEqual(self.leaf_matches(result), set(), path.name)
            self.assertNotIn('comparison_driven_reordering', self.routes(result), path.name)
            self.assertNotIn('interval_lookup', self.routes(result), path.name)

    def test_A5_mixed_function_reports_both_algorithms(self):
        # v2.1 (doc 07): neither algorithm explains the whole function, so both are
        # reported as CONTAINED, never as the identification of the function
        result = self.scan(POC / 'mixed.py')
        self.assertEqual({x['label'] for x in result['leaves'] if x['result'] == 'CONTAINS'},
                         {'ref_bubble_py', 'ref_binary_py'})
        self.assertEqual(self.leaf_matches(result), set())

    def test_A5b_independent_candidate_that_ap11_missed(self):
        result = self.scan(REPO / 'older_code' / 'semgrep_prolog_poc' / 'examples' / 'candidate.py')
        self.assertEqual(self.leaf_matches(result), {'ref_binary_py'})

    def test_A6_learn_corpus_from_ap11_store_read_only_with_qualified_identity(self):
        sys.path.insert(0, str(REPO / 'older_code' / 'algo_reference_corpus'))
        from ap11.database import add, connect
        from ap11.ingest import record
        with tempfile.TemporaryDirectory(prefix='ap13_corpus_') as td:
            corpus, ap11_store, store = Path(td) / 'corpus', Path(td) / 'ap11', Path(td) / 'store'
            (corpus / 'sorts').mkdir(parents=True)
            (corpus / 'searches').mkdir(parents=True)
            shutil.copy(EX / 'bubble' / 'bubble.py', corpus / 'sorts' / 'bubble.py')
            shutil.copy(EX / 'binary_search' / 'binary_search.py', corpus / 'searches' / 'binary_search.py')
            body = (EX / 'bubble' / 'bubble.py').read_text().replace('def bubble_sort(items)',
                                                                    'def sort(self, items)')
            indented = '\n'.join('    ' + x for x in body.splitlines())
            (corpus / 'sorts' / 'two.py').write_text(f'class A:\n{indented}\n\nclass B:\n{indented}\n')
            rows = [('sorts', 'sorts/bubble.py', 'bubble_sort'), ('searches', 'searches/binary_search.py',
                    'binary_search'), ('sorts', 'sorts/two.py', 'sort')]
            with connect(ap11_store) as db:
                for cat, rel, fn in rows:
                    add(db, record(label=f'py_{fn}_{cat}', commit='0' * 40, category=cat, relative=rel,
                                   function=fn, status='generated'))
            before = (ap11_store / 'references.sqlite3').read_bytes()
            r = cli('--store', store, 'learn-corpus', corpus, ap11_store)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('generated=4', r.stdout)          # two.py yields A.sort and B.sort
            self.assertIn('py_sort_sorts__A_sort', r.stdout)
            self.assertIn('py_sort_sorts__B_sort', r.stdout)
            again = cli('--store', store, 'learn-corpus', corpus, ap11_store)
            self.assertIn('already_present=4', again.stdout)
            self.assertEqual((ap11_store / 'references.sqlite3').read_bytes(), before)

    def test_A7_missing_swipl_is_explicit_error(self):
        with tempfile.TemporaryDirectory() as empty:  # cli runs via absolute sys.executable
            env = dict(os.environ, PATH=empty)
            r = cli('--store', self.store, 'scan', EX / 'bubble' / 'bubble.py', env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn('swipl not found', r.stderr)


if __name__ == '__main__':
    unittest.main()

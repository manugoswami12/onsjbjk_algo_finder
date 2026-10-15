"""AP12 independent coverage, strict-first fallback and immutability acceptance."""
from __future__ import annotations

import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ap11.database import connect
from ap12 import full_ingest, scan_auto
from ap12.storage import db_open
from ap12.verify import inspect

ROOT=Path(__file__).resolve().parents[1]


class FakeReference:
    def functions(self, tree):
        return [(('Pr',i),name,None,None) for i,name in enumerate(tree['names'])]

    def path_string(self, path):
        return '/'.join(map(str,path))

    def compile_reference(self, ast_file,label,function,kind,ordinal,draft):
        draft.write_text(f"% generated in fake test\nreference_pattern('{label}','body',obj([]),[]).\n",encoding='utf8')


def fake_capture(path, destination):
    parsed=ast.parse(path.read_text(encoding='utf8'))
    names=[x.name for x in parsed.body if isinstance(x,ast.FunctionDef)]
    destination.write_text(json.dumps({'names':names}),encoding='utf8')


def fake_fallback(path):
    functions=[x.name for x in ast.parse(path.read_text()).body if isinstance(x,ast.FunctionDef)]
    if not functions:
        return 'no_functions','',[]
    facts=''.join(f'program(f{i},anonymous).\n' for i in range(1,len(functions)+1))
    facts+=''.join(f'observed(f{i},returned_input,1).\n' for i in range(1,len(functions)+1))
    return ('routed',facts,[dict(function=f,routes=['sequence_rearrangement'],
                               evidence={'returned_input':[1]},limitations=[])
                            for f in functions])


def git(*cmd):
    subprocess.run(['git',*map(str,cmd)],check=True,capture_output=True)


class AP12Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.work=Path(self.tmp.name)
        self.corpus=self.work/'TheAlgorithms_Python'
        self.corpus.mkdir()
        git('-C',self.corpus,'init','-q')
        git('-C',self.corpus,'config','user.email','local@example.invalid')
        git('-C',self.corpus,'config','user.name','Local')
        git('-C',self.corpus,'remote','add','origin','https://github.com/TheAlgorithms/Python.git')
        for rel,source in {
            'sorts/test.py':'def alpha(x):\n    return x\n',
            'searches/test.py':'def beta(a, x):\n    return a[x]\n',
            'blank.py':'# tracked Python file without functions\n',
        }.items():
            path=self.corpus/rel
            path.parent.mkdir(exist_ok=True,parents=True)
            path.write_text(source,encoding='utf8')
        git('-C',self.corpus,'add','.')
        git('-C',self.corpus,'commit','-qm','pinned-test')
        self.store=self.work/'store'
        self.mock_api=patch.object(full_ingest,'api',return_value=(
            FakeReference(),SimpleNamespace(),None,
            lambda path:json.loads(path.read_text(encoding='utf8'))))
        self.mock_api.start()
        self.addCleanup(self.mock_api.stop)

    def execute(self,**kwargs):
        with redirect_stdout(io.StringIO()):
            return full_ingest.run(self.corpus,self.store,capture_fn=fake_capture,
                                   fallback_fn=fake_fallback,verbose=False,**kwargs)

    def test_complete_source_inventory_and_all_functions_and_root(self):
        report=self.execute()
        self.assertEqual(report['tracked_sources'],3)
        self.assertEqual(report['represented_sources'],3)
        self.assertTrue(report['all_files_accounted'])
        self.assertEqual(report['missing_sources'],[])
        self.assertEqual(report['generated_ap11_clauses'],2)
        with connect(self.store) as db:
            rows=db.execute('SELECT status,review_status FROM reference').fetchall()
            self.assertEqual(len(rows),3)
            self.assertEqual({r['review_status'] for r in rows},{'unreviewed'})
        with db_open(self.store) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM source_file').fetchone()[0],3)
            self.assertEqual(db.execute('SELECT count(*) FROM observation').fetchone()[0],2)

    def test_bounded_batch_then_resume_is_complete(self):
        part=self.execute(max_files=1)
        self.assertFalse(part['all_files_accounted'])
        self.assertEqual(len(part['missing_sources']),2)
        completed=self.execute()
        self.assertTrue(completed['all_files_accounted'])
        with patch.object(full_ingest,'compile_one',side_effect=AssertionError('should skip')):
            again=self.execute()
        self.assertTrue(again['all_files_accounted'])

    def test_corrupt_ap11_pattern_must_fail_on_resume(self):
        self.execute()
        with connect(self.store) as db:
            clause=db.execute("SELECT clause_path FROM reference WHERE status='generated' LIMIT 1").fetchone()[0]
        (self.store/clause).write_text('corrupted',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'corrupted'):
            self.execute()

    def test_corrupt_ap12_facts_must_fail_on_resume(self):
        self.execute()
        with db_open(self.store) as db:
            clause=db.execute('SELECT fact_path FROM source_file WHERE fact_path!="" LIMIT 1').fetchone()[0]
        (self.store/clause).write_text('wrong',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'missing or modified'):
            self.execute()

    def test_modified_git_checkout_rejected(self):
        (self.corpus/'sorts/test.py').write_text('def alpha(x): return 5\n')
        with self.assertRaisesRegex(ValueError,'tracked corpus has edits'):
            self.execute()

    def test_source_parse_error_explicit_not_silent(self):
        def failed_capture(path,dst):
            if path.name=='test.py': raise ValueError('broken capture on purpose')
            return fake_capture(path,dst)
        with redirect_stdout(io.StringIO()):
            r=full_ingest.run(self.corpus,self.store,capture_fn=failed_capture,
                              fallback_fn=fake_fallback,verbose=False)
        self.assertTrue(r['all_files_accounted'])
        self.assertGreater(r['error_sources'],0)
        self.assertEqual(r['generated_ap11_clauses'],0)

    def test_fallback_route_does_not_approve_ap11_refs(self):
        self.execute()
        with connect(self.store) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reference WHERE review_status='approved'").fetchone()[0],0)
        with db_open(self.store) as db:
            self.assertGreater(db.execute('SELECT COUNT(*) FROM observation').fetchone()[0],0)

    def test_strict_first_per_function_not_file_wide(self):
        source=self.corpus/'sorts/test.py'
        reply="AP11_SCAN: references=1\nAP10_THREAD: x; function: alpha; region: 'body'\n"
        with redirect_stdout(io.StringIO()) as output:
            result=scan_auto.scan(source,self.store,exact_scan=lambda *a:reply,
                                  fallback=lambda *a: (_ for _ in ()).throw(AssertionError('must not fall back')))
        self.assertEqual(result['strict_functions'],['alpha'])
        self.assertFalse(result['fallback_functions'])

    def test_automatic_fallback_on_unknown(self):
        source=self.corpus/'sorts/test.py'
        with redirect_stdout(io.StringIO()) as output:
            result=scan_auto.scan(source,self.store,exact_scan=lambda *a:'AP11_UNKNOWN\n',
                                  fallback=fake_fallback)
        self.assertEqual(result['strict_functions'],[])
        self.assertEqual(result['fallback_functions'][0]['routes'],['sequence_rearrangement'])
        self.assertIn('CANDIDATES ONLY',output.getvalue())

    def test_existing_source_with_different_frozen_hash_rejected(self):
        self.execute()
        with connect(self.store) as db:
            label=db.execute('SELECT label FROM reference WHERE status="generated" LIMIT 1').fetchone()[0]
            db.execute('UPDATE reference SET source_sha256="incorrect" WHERE label=?',(label,))
        with self.assertRaisesRegex(ValueError,'source hash'):
            self.execute()


if __name__=='__main__':
    unittest.main()

class StaticRouteOverlayTests(unittest.TestCase):
    def test_real_archive_binary_search_has_three_conservative_interval_witnesses(self):
        from ap12.interval_evidence import enrich
        import sys
        poc=ROOT.parent/'onsjbjk_algo_io_fallback_poc_v0_1'
        if str(poc) not in sys.path:sys.path.insert(0,str(poc))
        from run_poc import load
        source=ROOT/'TheAlgorithms_Python/searches/binary_search.py'
        analyses=enrich(load(source),source.read_text(encoding='utf-8-sig'))
        observed={x.name for x in analyses if 'bounded_indexed_interval_lookup' in x.evidence}
        self.assertEqual(observed,{'bisect_left','bisect_right','binary_search'})
        self.assertNotIn('binary_search_std_lib',observed)
        self.assertNotIn('binary_search_by_recursion',observed)

    def test_frozen_poc_bad_examples_do_not_gain_interval_evidence(self):
        from ap12.interval_evidence import enrich
        import sys
        poc=ROOT.parent/'onsjbjk_algo_io_fallback_poc_v0_1'
        if str(poc) not in sys.path:sys.path.insert(0,str(poc))
        from run_poc import load
        for name in ('fake_midpoint.py','unrelated_compare.py','unrelated_array.py',
                     'wrong_exchange.py','linear.py','unknown_call.py'):
            p=poc/'examples'/name
            a=enrich(load(p),p.read_text(encoding='utf8'))
            self.assertFalse(any('bounded_indexed_interval_lookup' in x.evidence for x in a),name)

    def test_branch_to_category_uses_observed_evidence_not_source_name(self):
        from ap12.scan_auto import BRANCH_CATEGORIES
        self.assertEqual(BRANCH_CATEGORIES['interval_lookup'],'searches')
        self.assertNotIn('unknown',BRANCH_CATEGORIES)

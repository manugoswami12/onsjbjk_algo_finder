"""Offline acceptance using actual AP10 captured Semgrep JSON and frozen AP9 compiler."""
from __future__ import annotations

from contextlib import redirect_stdout
from pathlib import Path
import hashlib
import io
import os
import shutil
import sqlite3
import subprocess
import tempfile
import unittest

from ap11.bridge import api, frozen_root
from ap11.database import approve, connect, get, summary
from ap11.ingest import ingest
from ap11.recognize import scan
from ap11.source import inventory, label_for, revision, source_path, verify_origin

ROOT = Path(__file__).resolve().parents[1]
FROZEN = frozen_root()


class SQLiteConnectionLifecycleTests(unittest.TestCase):
    def test_context_exits_close_sqlite_handle(self):
        """Regression: sqlite3.Connection.__exit__ alone never closes on Windows."""
        with tempfile.TemporaryDirectory() as d:
            store = Path(d) / 'store'
            with connect(store) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM reference').fetchone()[0], 0)
                # Nested with db is used by add()/approve() and must remain valid.
                with db:
                    db.execute('SELECT 1')
            # Test closure even on POSIX, where an open database can be unlinked.
            with self.assertRaises(sqlite3.ProgrammingError):
                db.execute('SELECT 1')
            self.assertTrue((store / 'references.sqlite3').is_file())
        self.assertFalse(store.exists())

    def test_context_exceptions_rollback_and_close(self):
        with tempfile.TemporaryDirectory() as d:
            store = Path(d) / 'store'
            with self.assertRaisesRegex(RuntimeError, 'rollback-check'):
                with connect(store) as db:
                    db.execute("INSERT INTO reference (label,language,repository,git_commit,category,relative_path,function_name,status) "
                               "VALUES ('x','Python','r','c','sorts','x.py','f','generated')")
                    raise RuntimeError('rollback-check')
            with self.assertRaises(sqlite3.ProgrammingError):
                db.execute('SELECT 1')
            with connect(store) as check:
                self.assertEqual(check.execute('SELECT COUNT(*) FROM reference').fetchone()[0], 0)
            with self.assertRaises(sqlite3.ProgrammingError):
                check.execute('SELECT 1')


class SourceTests(unittest.TestCase):
    def test_stable_safe_unique_labels(self):
        a = label_for('a' * 40, 'sorts/a.py', 'bubble')
        self.assertTrue(a.startswith('py_'))
        self.assertLessEqual(len(a), 64)
        self.assertEqual(a, label_for('a' * 40, 'sorts/a.py', 'bubble'))
        self.assertNotEqual(a, label_for('a' * 40, 'hashes/a.py', 'bubble'))
        self.assertNotEqual(a, label_for('b' * 40, 'sorts/a.py', 'bubble'))

    def test_reject_traversal_and_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'sorts').mkdir()
            (root / 'sorts' / 'ok.py').write_text('pass', encoding='utf8')
            self.assertTrue(source_path(root, 'sorts/ok.py').is_file())
            with self.assertRaises(ValueError):
                source_path(root, '../bad.py')
            try:
                (root / 'sorts' / 'alias.py').symlink_to(root / 'sorts' / 'ok.py')
            except (OSError, NotImplementedError):
                return
            with self.assertRaises(ValueError):
                source_path(root, 'sorts/alias.py')


@unittest.skipUnless((FROZEN / 'tools/reference_pattern.py').exists(),
                     'exact AP10 sibling is not available')
class FrozenInterfaceTests(unittest.TestCase):
    def test_real_ast_frozen_compile_no_edits(self):
        ref, _, bundler, strict_load = api()
        ast = FROZEN / 'out/ap10/sort_signature.json'
        self.assertEqual([x[1] for x in ref.functions(strict_load(ast))], ['sort_reference'])
        original = FROZEN / 'tools/reference_pattern.py'
        before = hashlib.sha256(original.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as d:
            result = Path(d) / 'label.pl'
            info = ref.compile_reference(ast, 'test_reference', 'sort_reference', 'body', 0, result)
            self.assertEqual(info['reference_function'], 'sort_reference')
            self.assertIn('reference_pattern(', result.read_text(encoding='utf8'))
            self.assertIn('binding(', result.read_text(encoding='utf8'))
            bundle = bundler.bundle_references([('test_reference', result)], Path(d) / 'all.pl')
            self.assertEqual(bundle.read_text().count('reference_pattern('), 1)
        self.assertEqual(before, hashlib.sha256(original.read_bytes()).hexdigest())


@unittest.skipUnless(shutil.which('git') and (FROZEN / 'out/ap10/sort_signature.json').exists(),
                     'git and real AP10 capture required')
class EndToEndOfflineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.corpus = root / 'repo'
        self.store = root / 'store'
        (self.corpus / 'sorts').mkdir(parents=True)
        (self.corpus / 'hashes').mkdir()
        for category, name in (('sorts', 'sort'), ('hashes', 'hash')):
            shutil.copyfile(FROZEN / 'examples' / f'ap10_{name}_reference.py',
                            self.corpus / category / f'{name}.py')
        subprocess.run(['git', 'init', '-q', str(self.corpus)], check=True)
        subprocess.run(['git', '-C', str(self.corpus), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.corpus), '-c', 'user.name=Test',
                        '-c', 'user.email=unit@example.org', 'commit', '-qm', 'fixture'], check=True)

    def capture(self, path, destination):
        name = 'sort_signature' if path.parent.name == 'sorts' else 'hash_signature'
        shutil.copyfile(FROZEN / 'out/ap10' / (name + '.json'), destination)
        return destination

    def test_real_compiler_separate_store_resumption_and_review(self):
        before = hashlib.sha256((FROZEN / 'out/ap10/catalog.json').read_bytes()).hexdigest()
        with redirect_stdout(io.StringIO()):
            result = ingest(self.corpus, self.store, ('sorts', 'hashes'),
                            limit=30, capture_fn=self.capture, require_origin=False)
        self.assertEqual(result['run_counts']['generated'], 2)
        self.assertEqual(result['repository'], 'https://github.com/TheAlgorithms/Python.git')
        with connect(self.store) as db:
            rows = db.execute("SELECT * FROM reference WHERE status='generated'").fetchall()
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(r['review_status'] == 'unreviewed' for r in rows))
            self.assertTrue(all((self.store / r['clause_path']).is_file() for r in rows))
            approve(db, rows[0]['label'], 'approved')
        with redirect_stdout(io.StringIO()):
            replay = ingest(self.corpus, self.store, ('sorts', 'hashes'),
                            limit=30, capture_fn=self.capture, require_origin=False)
        self.assertEqual(replay['run_counts']['already_present'], 2)
        with connect(self.store) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reference").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reference WHERE review_status='approved'").fetchone()[0], 1)
        self.assertEqual(before, hashlib.sha256((FROZEN / 'out/ap10/catalog.json').read_bytes()).hexdigest())

    def test_fake_git_origin_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_origin(self.corpus)

    def test_bundle_two_generated_clauses(self):
        with redirect_stdout(io.StringIO()):
            ingest(self.corpus, self.store, ('sorts', 'hashes'), 30,
                   capture_fn=self.capture, require_origin=False)
        with connect(self.store) as db:
            rows = db.execute("SELECT * FROM reference WHERE status='generated'").fetchall()
        _, _, bundler, _ = api()
        pairs = [(r['label'], self.store / r['clause_path']) for r in rows]
        result = bundler.bundle_references(pairs, self.store / 'two.pl')
        clauses = [s for s in result.read_text().splitlines() if s.startswith('reference_pattern(')]
        self.assertEqual(len(clauses), 2)

    def test_reject_changed_tracked_checkout(self):
        (self.corpus / 'sorts/sort.py').write_text('changed', encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'tracked corpus has edits'):
            revision(self.corpus)

    def test_detect_corrupted_clause_before_resume(self):
        with redirect_stdout(io.StringIO()):
            ingest(self.corpus, self.store, ('sorts',), 30, capture_fn=self.capture, require_origin=False)
        with connect(self.store) as db:
            row = db.execute('SELECT * FROM reference').fetchone()
        (self.store / row['clause_path']).write_text(':- initialization(halt).')
        with self.assertRaisesRegex(ValueError, 'corrupted immutable clause'):
            with redirect_stdout(io.StringIO()):
                ingest(self.corpus, self.store, ('sorts',), 30, capture_fn=self.capture, require_origin=False)

    def test_git_inventory_fair_between_categories(self):
        files = inventory(self.corpus, ('sorts', 'hashes'), 100000)
        self.assertEqual([c for c, _ in files], ['sorts', 'hashes'])

    def test_scan_requires_review(self):
        with redirect_stdout(io.StringIO()):
            ingest(self.corpus, self.store, ('sorts',), 30, capture_fn=self.capture, require_origin=False)
        answer = scan(self.store, self.corpus / 'sorts/sort.py')
        self.assertIn('no eligible references', answer)
        with connect(self.store) as db:
            approve(db, db.execute('SELECT label FROM reference').fetchone()[0], 'approved')
        # Actual scanning needs Semgrep and SWI-Prolog; no offline false pass claim.

    def test_parse_failure_is_reported_not_success(self):
        def failed_capture(path, destination):
            raise ValueError('intentionally unsupported fixture')
        with redirect_stdout(io.StringIO()):
            output = ingest(self.corpus, self.store, ('sorts',), 30,
                            capture_fn=failed_capture, require_origin=False)
        self.assertEqual(output['run_counts']['parse_errors'], 1)
        with connect(self.store) as db:
            row = db.execute('SELECT status,reason FROM reference').fetchone()
            self.assertEqual(row['status'], 'error')
            self.assertIn('unsupported', row['reason'])


if __name__ == '__main__':
    unittest.main()

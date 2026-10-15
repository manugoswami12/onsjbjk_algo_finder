"""Exhaustive, resumable source-only TheAlgorithms/Python -> AP11 + AP12.

Uses frozen AP9 compiler and AP11 schema through their existing public APIs.
Does not execute any upstream Python. Writes only to AP11 store and separate AP12 overlay.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from ap11.bridge import api
from ap11.database import add, connect, get
from ap11.ingest import IntegrityError, record
from ap11.source import REPOSITORY, label_for, revision, sha256, source_path, verify_origin
from .storage import db_open, save, validated_file

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'TheAlgorithms_Python'
STORE = ROOT / 'store'


def manifest(corpus: Path) -> tuple[str,list[str]]:
    corpus = corpus.resolve(strict=True)
    commit = revision(corpus)
    verify_origin(corpus)
    p = subprocess.run(['git','-C',str(corpus),'ls-files','-z'],
                       capture_output=True, timeout=45, check=True)
    paths = sorted({name.decode('utf8','strict').replace('\\','/')
                    for name in p.stdout.split(b'\0') if name.endswith(b'.py')})
    for rel in paths:
        source_path(corpus,rel)  # immediately fail for untrusted symlinks / paths
    if not paths:
        raise ValueError('no tracked Python sources in pinned checkout')
    return commit, paths


def check_ap11_file(store: Path, conn, commit: str, relative: str, source_hash: str):
    rows = conn.execute('''SELECT * FROM reference WHERE git_commit=? AND relative_path=?
                           ORDER BY function_name''',(commit,relative)).fetchall()
    for item in rows:
        if item['source_sha256'] != source_hash:
            raise IntegrityError('AP11 source hash changed: '+relative)
        if item['status'] == 'generated':
            p = (store / item['clause_path']).resolve()
            if not p.is_relative_to((store / 'refs').resolve()):
                raise IntegrityError('AP11 clause outside store: ' + relative)
            if not p.is_file() or sha256(p.read_bytes()) != item['pattern_sha256']:
                raise IntegrityError('AP11 clause corrupted: '+relative)
    return rows


def compile_one(corpus,store,commit,relative,source_hash, reference,ap10,strict_load,
                max_source_bytes, capture_fn=None):
    """Preserve existing immutable AP11 rows; record failures rather than drop files."""
    path = source_path(corpus,relative)
    category = relative.split('/',1)[0] if '/' in relative else '_root'
    if path.stat().st_size > max_source_bytes:
        return file_marker(store,commit,category,relative,source_hash,
                           'file exceeds --max-source-kib')
    with tempfile.TemporaryDirectory(prefix='ap12_capture_', dir=store / 'temp') as td:
        ast_file = Path(td)/'ast.json'
        try:
            (capture_fn or ap10.capture)(path,ast_file)
            if not ast_file.is_file():
                raise ValueError('Semgrep AST not produced')
            if ast_file.stat().st_size > 16*1024*1024:
                raise ValueError('Semgrep AST >16 MiB capture limit')
            ast_hash = sha256(ast_file.read_bytes())
            occurrences = list(reference.functions(strict_load(ast_file)))
            if not occurrences:
                return file_marker(store,commit,category,relative,source_hash,
                                   'no supported function in captured AST',status='skipped')
        except (OSError, ValueError, TypeError, RecursionError, subprocess.TimeoutExpired) as exc:
            return file_marker(store,commit,category,relative,source_hash,str(exc))
        names = Counter(name for _,name,_,_ in occurrences)
        statuses = Counter()
        with connect(store) as db:
            for fpath,fname,_,_ in occurrences:
                label = label_for(commit,relative,fname)
                old = get(db,label)
                if old:
                    if old['source_sha256']!=source_hash or old['ast_sha256']!=ast_hash:
                        raise IntegrityError('immutable AP11 reference changed: '+label)
                    check_ap11_file(store,db,commit,relative,source_hash)
                    statuses[old['status']]+=1
                    continue
                base = record(label=label,commit=commit,category=category,
                              relative=relative,function=fname,
                              function_path=reference.path_string(fpath),
                              source_hash=source_hash,ast_hash=ast_hash)
                if names[fname]!=1:
                    base.update(status='skipped', reason='duplicate function name within same source')
                    add(db,base); statuses['skipped']+=1
                    continue
                try:
                    draft = Path(td)/(label+'.pl')
                    reference.compile_reference(ast_file,label,fname,'body',0,draft)
                    data = draft.read_bytes()
                    # Same structural-hash convention as AP11, not a semantic fingerprint.
                    line = next(x for x in data.decode('utf8').splitlines()
                                if x.startswith('reference_pattern('))
                    structure = line.split(',',1)[1]
                    target = store / 'refs' / (label+'.pl')
                    if target.exists():
                        if target.read_bytes()!=data:
                            raise IntegrityError('orphan AP11 clause conflicts: '+label)
                    else:
                        draft.replace(target)
                    base.update(status='generated',clause_path='refs/'+target.name,
                                pattern_sha256=sha256(data),
                                structural_sha256=sha256(structure.encode('utf8')))
                    add(db,base); statuses['generated']+=1
                except IntegrityError:
                    raise
                except (OSError,ValueError,TypeError,RecursionError) as exc:
                    base.update(status='error', reason=str(exc))
                    add(db,base); statuses['error']+=1
        if statuses['error']:
            status='partial_error'
        elif statuses['skipped']:
            status='partial_skipped'
        else:
            status='generated'
        return status,sum(statuses.values())


def file_marker(store,commit,category,relative,source_hash,reason,status='error'):
    label=label_for(commit,relative,'@file')
    with connect(store) as db:
        old=get(db,label)
        if old:
            if old['source_sha256']!=source_hash:
                raise IntegrityError('immutable AP11 file marker changed: '+label)
            return old['status'],0
        add(db,record(label=label,commit=commit,category=category,relative=relative,
                      function='@file',source_hash=source_hash,
                      status=status,reason=reason))
    return status,0


def collect_fallback(path: Path):
    """Call the separate AP12 bridge. Both frozen toolchains stay unmodified."""
    from .fallback_bridge import collect
    return collect(path)


def run(corpus=CORPUS,store=STORE,max_files=None,max_source_kib=1024,
        capture_fn=None, fallback_fn=None, verbose=True):
    from .verify import inspect
    corpus=Path(corpus).resolve(strict=True)
    store=Path(store).resolve()
    if store==corpus or corpus in store.parents:
        raise ValueError('store cannot be inside corpus')
    if not store.is_relative_to(ROOT.resolve()):
        raise ValueError('store must remain beneath algo_reference_corpus')
    if max_files is not None and max_files<1:
        raise ValueError('--max-files must be positive')
    if max_source_kib < 1 or max_source_kib>4096:
        raise ValueError('--max-source-kib must be 1..4096')
    commit,paths=manifest(corpus)
    reference,ap10,_,strict_load=api()
    (store/'refs').mkdir(parents=True,exist_ok=True)
    (store/'temp').mkdir(parents=True,exist_ok=True)
    attempted=0
    for relative in paths[:max_files]:
        path=source_path(corpus,relative)
        source_hash=sha256(path.read_bytes())
        with db_open(store) as ledger,connect(store) as existing_db:
            prior=ledger.execute('''SELECT * FROM source_file WHERE git_commit=?
                                    AND relative_path=?''',(commit,relative)).fetchone()
            if prior:
                if prior['source_sha256']!=source_hash:
                    raise IntegrityError('AP12 source hash changed: '+relative)
                validated_file(store,prior)
                rows=check_ap11_file(store,existing_db,commit,relative,source_hash)
                if len(rows)!=prior['exact_count'] and prior['exact_status'] not in ('error','skipped'):
                    raise IntegrityError('AP11 count differs from checkpoint: '+relative)
                if verbose: print(f'AP12_PRESENT: {relative}',flush=True)
                attempted+=1
                continue
        exact_status='error'; exact_count=0; fallback_status='error'; facts=''; observations=[]; failures=[]
        try:
            exact_status,exact_count=compile_one(corpus,store,commit,relative,
                source_hash,reference,ap10,strict_load,max_source_kib*1024,capture_fn)
            if exact_status in ('error','partial_error','partial_skipped'):
                failures.append('AP11 templates: '+exact_status)
        except IntegrityError:
            raise
        except (OSError,ValueError,TypeError,RecursionError,subprocess.TimeoutExpired) as exc:
            # No silent skip: try to persist an exact source marker, then disclose error.
            file_marker(store,commit,relative.split('/')[0] if '/' in relative else '_root',
                        relative,source_hash,str(exc))
            failures.append('AP11: '+str(exc))
        try:
            fallback_status,facts,observations=(fallback_fn or collect_fallback)(path)
        except (OSError,ValueError,TypeError,RuntimeError,SyntaxError,
                subprocess.TimeoutExpired,UnicodeError) as exc:
            failures.append('fallback: '+str(exc));fallback_status='error'
        save(store,commit,relative,source_hash,exact_status,exact_count,fallback_status,
             facts,observations,'; '.join(failures))
        attempted+=1
        if verbose:
            print(f'AP12_PROGRESS: {attempted}/{len(paths)} {relative} '
                  f'AP11={exact_status}:{exact_count} FALLBACK={fallback_status}',flush=True)
    report=inspect(corpus,store,manifest_result=(commit,paths))
    report['batch_files_visited']=attempted
    report['max_files']=max_files
    destination=store/'ap12_full_report.json'
    temporary=destination.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf8')
    temporary.replace(destination)
    print('AP12_FULL_REPORT:',destination)
    print('AP12_FULL_COVERAGE:', 'PASS' if report['all_files_accounted'] else 'INCOMPLETE',
          f"tracked={report['tracked_sources']} represented={report['represented_sources']} "
          f"missing={len(report['missing_sources'])} errors={report['error_sources']}",flush=True)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-files',type=int,help='pilot: only first N tracked sources')
    parser.add_argument('--max-source-kib',type=int,default=1024)
    args=parser.parse_args(argv)
    try:
        result=run(max_files=args.max_files,max_source_kib=args.max_source_kib)
        # A complete, safely accounted corpus may contain genuine compiler/analysis
        # failures. Do not label it complete successful conversion.
        return 0 if result['all_files_accounted'] and result['error_sources']==0 else (0 if args.max_files else 2)
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired,IntegrityError) as exc:
        print('AP12_FULL_ERROR:',exc,file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())

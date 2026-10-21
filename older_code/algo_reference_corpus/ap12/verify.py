"""Independent Git-manifest and cryptographic coverage verification for AP12."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from ap11.database import connect
from ap11.source import sha256, source_path
from .storage import db_open, validated_file

ROOT=Path(__file__).resolve().parents[1]


def inspect(corpus: Path, store: Path, manifest_result=None):
    from .full_ingest import manifest
    corpus=Path(corpus).resolve(strict=True)
    store=Path(store).resolve()
    commit,paths=manifest_result if manifest_result is not None else manifest(corpus)
    wanted=set(paths)
    with db_open(store) as ledger, connect(store) as ap11db:
        rows=list(ledger.execute('SELECT * FROM source_file WHERE git_commit=?',(commit,)))
        by_path={r['relative_path']:r for r in rows}
        missing=sorted(wanted-set(by_path))
        extra=sorted(set(by_path)-wanted)
        errors=[]; fallback_unknown=0; source_error=0; generated=0; skipped=0; fallback_no_functions=0
        for relative in sorted(wanted & set(by_path)):
            row=by_path[relative]
            if sha256(source_path(corpus,relative).read_bytes())!=row['source_sha256']:
                raise ValueError('AP12 source changed: '+relative)
            validated_file(store,row)
            ap11rows=ap11db.execute('''SELECT status,source_sha256,clause_path,pattern_sha256
                                          FROM reference WHERE git_commit=? AND relative_path=?''',
                                      (commit,relative)).fetchall()
            if not ap11rows:
                raise ValueError('AP11 missing source row: '+relative)
            for ref in ap11rows:
                if ref['source_sha256']!=row['source_sha256']:
                    raise ValueError('AP11 source hash differs: '+relative)
                if ref['status']=='generated':
                    target=(store/ref['clause_path']).resolve()
                    if not target.is_relative_to((store/'refs').resolve()):
                        raise ValueError('AP11 invalid clause path: '+relative)
                    if not target.is_file() or sha256(target.read_bytes())!=ref['pattern_sha256']:
                        raise ValueError('AP11 invalid clause hash: '+relative)
                    generated+=1
            if row['exact_status'] not in ('error','skipped') and len(ap11rows)!=row['exact_count']:
                raise ValueError('AP11 unexpected number of function rows: '+relative)
            if row['fallback_status']=='unknown_only':fallback_unknown+=1
            if row['fallback_status']=='no_functions':fallback_no_functions+=1
            if row['exact_status'] in ('skipped','partial_skipped'):skipped+=1
            if row['exact_status'] in ('error','partial_error','partial_skipped') or row['fallback_status']=='error':
                errors.append(dict(path=relative,exact=row['exact_status'],
                                   fallback=row['fallback_status'],reason=row['error']))
            if any(ref['status']=='error' for ref in ap11rows):
                source_error+=1
            count=ledger.execute('SELECT count(*) FROM observation WHERE git_commit=? AND relative_path=?',
                                 (commit,relative)).fetchone()[0]
            if row['fact_path'] and count<1:
                raise ValueError('AP12 facts exist but observations missing: '+relative)
            if row['fallback_status'] in ('routed','unknown_only') and (not row['fact_path'] or count<1):
                raise ValueError('AP12 observation facts absent: '+relative)
        return dict(repository='https://github.com/TheAlgorithms/Python.git',git_commit=commit,
                    tracked_sources=len(paths),represented_sources=len(wanted & set(by_path)),
                    all_files_accounted=not missing and not extra,
                    missing_sources=missing,extra_sources=extra,
                    error_sources=len(errors),error_details=errors,
                    ap11_files_with_error_rows=source_error,
                    generated_ap11_clauses=generated,
                    fallback_unknown_only_files=fallback_unknown,
                    fallback_no_top_level_functions_files=fallback_no_functions,
                    ap11_skipped_sources=skipped,
                    disclaimer='coverage != successful recognition or semantic equivalence')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',type=Path,default=ROOT/'TheAlgorithms_Python')
    parser.add_argument('--store',type=Path,default=ROOT/'store')
    args=parser.parse_args(argv)
    try:
        r=inspect(args.corpus,args.store)
        print(json.dumps(r,indent=2))
        return 0 if r['all_files_accounted'] and r['error_sources']==0 else 2
    except (OSError,ValueError) as exc:
        print('AP12_VERIFY_ERROR:',exc,file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())

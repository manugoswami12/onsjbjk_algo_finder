"""Strict AP11 recognition first; call INDEPENDENT fallback for unmatched functions.

No review-state changes. Candidate routes cannot become strict algorithm matches.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from ap11.recognize import scan as strict_scan
from .full_ingest import collect_fallback, ROOT


BRANCH_CATEGORIES = {
    'sequence_rearrangement': 'sorts',
    'comparison_driven_reordering': 'sorts',
    'indexed_lookup': 'searches',
    'interval_lookup': 'searches',
}


def strict_names(report: str):
    # The frozen scanner output contains `AP10_THREAD: label; function: name; ...`.
    return set(re.findall(r'AP10_THREAD: [^;\n]+; function: ([^;\n]+);',report))


def scan(source: Path, store: Path, category=None, include_unreviewed=False,
         limit=100, exact_scan=None, fallback=None):
    if not source.is_file() or source.suffix.lower()!='.py':
        raise ValueError('source must be an existing Python file')
    exact=(exact_scan or strict_scan)(store,source,category,
                                     include_unreviewed,limit)
    print('=== FROZEN AP11 STRICT RESULTS ===')
    print(exact,end='' if exact.endswith('\n') else '\n')
    names=strict_names(exact)
    truncated=('truncated=True' in exact)
    # Deliberately keep fallback completely independent of candidate identity.
    from ast import parse, FunctionDef, AsyncFunctionDef
    text=source.read_text(encoding='utf-8-sig')
    functions=[n.name for n in parse(text).body if isinstance(n,(FunctionDef,AsyncFunctionDef))]
    unmatched=[n for n in functions if n not in names]
    if not unmatched:
        print('AP12_AUTO_FALLBACK: not required; every discovered top-level function has strict evidence.')
        return {'strict_functions':sorted(names),'fallback_functions':[]}
    status,facts,observations=(fallback or collect_fallback)(source)
    print('=== AP12 AUTOMATIC FALLBACK: CANDIDATES ONLY ===')
    reports=[]
    categories=set()
    for obs in observations:
        if obs['function'] in names:continue
        print(f"AP12_BRANCH: function={obs['function']}; routes={','.join(obs['routes'])}; "
              f"evidence={','.join(sorted(obs['evidence']))}; "
              f"limitations={','.join(obs['limitations']) or 'none'}")
        reports.append(obs)
        categories.update(BRANCH_CATEGORIES[r] for r in obs['routes'] if r in BRANCH_CATEGORIES)
    # Branches only restrict the *catalog search*. They never change matcher
    # acceptance and cannot promote an unreviewed reference.
    if not category:
        for candidate_category in sorted(categories):
            print('AP12_PROLOG_BRANCH_TO_CATEGORY:',candidate_category)
            rerun=(exact_scan or strict_scan)(store,source,candidate_category,
                                               include_unreviewed,limit)
            print(rerun,end='' if rerun.endswith('\n') else '\n')
            names.update(strict_names(rerun))
            truncated=truncated or ('truncated=True' in rerun)
    if truncated:
        print('AP12_TRUNCATED: strict matches are not an exhaustive search of the catalog')
    print('AP12_NOTICE: Prolog candidate route is NOT algorithm identification or a proof.')
    return {'strict_functions':sorted(names),'fallback_functions':reports}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('--category')
    p.add_argument('--include-unreviewed',action='store_true')
    p.add_argument('--limit',type=int,default=100)
    args=p.parse_args(argv)
    try:
        scan(args.source,ROOT/'store',args.category,args.include_unreviewed,args.limit)
        return 0
    except (OSError,ValueError,RuntimeError,SyntaxError) as exc:
        print('AP12_SCAN_ERROR:',exc,file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())

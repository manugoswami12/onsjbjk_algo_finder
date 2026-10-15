"""Unchanged POC extraction + one bounded AP12 observation + independent SWI route."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from .interval_evidence import enrich

ROOT=Path(__file__).resolve().parents[1]
POC=ROOT.parent/'onsjbjk_algo_io_fallback_poc_v0_1'
ROUTER=Path(__file__).resolve().parent/'prolog'/'route_extended.pl'


def collect(path: Path):
    if not (POC/'static_trace.py').is_file() or not ROUTER.is_file():
        raise ValueError('missing independent fallback dependency')
    if str(POC) not in sys.path:sys.path.insert(0,str(POC))
    from run_poc import load, facts_from
    # Uses user-provided program only as TEXT; never imports/runs it.
    analyses=enrich(load(path),path.read_text(encoding='utf-8-sig'))
    if not analyses:
        return 'no_functions','',[]
    facts=facts_from(analyses)
    executable=shutil.which('swipl')
    if not executable:
        raise ValueError('SWI-Prolog not found on PATH')
    with tempfile.TemporaryDirectory(prefix='ap12_route_') as td:
        f=Path(td)/'facts.pl'
        f.write_text(facts,encoding='utf8')
        proc=subprocess.run([executable,'-q','-s',str(ROUTER),'-g','main','-t','halt','--',str(f)],
                            stdin=subprocess.DEVNULL,text=True,capture_output=True,timeout=25)
        if proc.returncode or proc.stderr.strip():
            raise RuntimeError('AP12 SWI-Prolog failure: '+(proc.stderr or proc.stdout)[-600:])
        routes={f'f{i}':[] for i in range(1,len(analyses)+1)}
        for line in proc.stdout.splitlines():
            parts=line.split()
            if len(parts)!=3 or parts[0]!='ROUTE' or parts[1] not in routes:
                raise RuntimeError('AP12 Prolog returned malformed response: '+line)
            routes[parts[1]].append(parts[2])
        if any(not group for group in routes.values()):
            raise RuntimeError('AP12 Prolog omitted a function')
    results=[]
    for i,analysis in enumerate(analyses,1):
        results.append(dict(function=analysis.name,routes=sorted(set(routes['f'+str(i)])),
                            evidence=analysis.evidence,limitations=analysis.unknowns))
    status='unknown_only' if all(x['routes']==['unknown'] for x in results) else 'routed'
    return status,facts,results

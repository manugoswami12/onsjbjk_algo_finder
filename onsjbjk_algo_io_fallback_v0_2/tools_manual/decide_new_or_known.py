"""Manual test (scratch): decide new version / new algorithm / undecided for a file, from full-coverage runs."""
import json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import crosslang_frontends, compare_learners, ta_classes
crosslang_frontends.install(lisp_sbcl=False)
compare_learners._ap13()
import io_trace


def decide(p):
    try:
        info = io_trace.run_functions(p)
    except Exception as e:
        return {'decision': 'undecided', 'why': 'no run: ' + type(e).__name__}
    full = {n for n, d in info.items() if d.get('runs') and not d.get('unsupported') and all(r[0] for r in d['runs'])}
    part = {n: f"{sum(1 for r in d['runs'] if r[0])}/{len(d['runs'])}" for n, d in info.items()
            if d.get('runs') and n not in full}
    try:
        rs = ta_classes.runs(p)
        cs = ta_classes.classes(p, rs)
    except Exception as e:
        return {'decision': 'undecided', 'why': 'check error ' + type(e).__name__}
    if cs is None:
        return {'decision': 'undecided', 'why': 'check timeout'}
    full_cs = {c for n, v in cs.items() if n in full for c in v}
    varied = {n for n in full if n in rs and len({o for _, o in rs[n][1]}) > 1}
    if len(full_cs) == 1:
        return {'decision': 'new_version', 'class': min(full_cs), 'partial': part}
    if len(full_cs) > 1:
        return {'decision': 'undecided', 'why': 'several classes ' + str(sorted(full_cs))}
    if varied:
        return {'decision': 'new_algorithm', 'functions': sorted(varied), 'partial': part}
    return {'decision': 'undecided', 'why': 'no full run', 'partial': part}


if __name__ == '__main__':
    root, files = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text())
    with ThreadPoolExecutor(4) as pool:
        out = dict(zip(files, pool.map(lambda f: decide(root / f), files)))
    Path(sys.argv[3]).write_text(json.dumps(out, indent=1))

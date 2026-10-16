#!/usr/bin/env python3
"""AP13 v4 (doc 10): behaviour catalog of the learned corpus and identification by
logic trace first, input->output second.

  learn:    python tools/io_catalog.py learn <TheAlgorithms checkout> <catalog.json>
  identify: python tools/io_catalog.py identify <source file> <catalog.json>

For every function: the logical signature, the effective outputs on the fixed battery,
and the logic-trace fingerprints (io_trace.py). A reference is NON-DISCRIMINATIVE (never
used) when its outputs are constant or equal to its input on every run.
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from env_run import ToolError  # noqa: E402
from io_trace import battery, run_functions  # noqa: E402

MIN_COMMON = 5          # at least this many inputs must run in both programs
MIN_SHARE = 0.7         # ... and this share of the battery


def describe(info):
    out = {}
    for name, d in info.items():
        runs = d['runs']
        if not runs or d['unsupported']:
            continue
        ok = [r for r in runs if r[0]]
        if len(ok) < MIN_COMMON:
            continue
        outs = [r[1] if r[0] else None for r in runs]
        okouts = {o for o in outs if o is not None}
        inputs = [repr(x[0]) if len(x) == 1 else repr(x) for x in battery(d['sig'])]
        identity = all(o is None or o == inp.replace(' ', '') for o, inp in zip(outs, inputs))
        out[name] = {'sig': list(d['sig']), 'outputs': outs, 'traces': [r[2] if r[0] else None for r in runs],
                     'discriminative': len(okouts) > 1 and not identity}
    return out


def learn(corpus: Path, catalog: Path, workers=4):
    files = sorted(p for p in corpus.rglob('*.py') if '.git' not in p.parts)

    def one(p):
        try:
            return p.relative_to(corpus).as_posix(), describe(run_functions(p)), None
        except (ToolError, ValueError, OSError, RecursionError, KeyError, IndexError, TypeError,
                AttributeError, StopIteration) as exc:
            return p.relative_to(corpus).as_posix(), {}, str(exc)[:200]
    cat, errors = {}, 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, (rel, funs, err) in enumerate(pool.map(one, files), 1):
            errors += err is not None
            for name, d in funs.items():
                cat[f'{rel}::{name}'] = d
            if n % 200 == 0:
                print(f'AP13_IO_LEARN: {n}/{len(files)} functions={len(cat)} errors={errors}', flush=True)
    catalog.write_text(json.dumps(cat), encoding='utf-8')
    disc = sum(d['discriminative'] for d in cat.values())
    print(f'AP13_IO_LEARN: files={len(files)} functions={len(cat)} discriminative={disc} errors={errors}')


def compare(a, b):
    """('logic' | 'io' | None) for candidate a against reference b (same signature)."""
    if a['sig'] != b['sig'] or len(a['outputs']) != len(b['outputs']):
        return None
    common = [i for i, (x, y) in enumerate(zip(a['outputs'], b['outputs'])) if x is not None and y is not None]
    if len(common) < max(MIN_COMMON, MIN_SHARE * len(a['outputs'])):
        return None
    if any(a['outputs'][i] != b['outputs'][i] for i in common):
        return None
    if len({a['outputs'][i] for i in common}) < 2:   # equal only where both are constant: no evidence
        return None
    traced = [i for i in common if a['traces'][i] is not None and b['traces'][i] is not None]
    if traced and all(a['traces'][i] == b['traces'][i] for i in common) and len(traced) >= MIN_COMMON:
        return 'logic'                      # equal reads/writes of input positions on every input
    return 'io'


EMPTY_TRACE = None   # set from the catalog: fingerprint of the empty trace


def identify(source: Path, cat: dict):
    global EMPTY_TRACE
    from io_trace import run_functions as rf
    me = describe(rf(source))
    result = {}
    for name, d in me.items():
        if not d['discriminative']:
            result[name] = {'outcome': 'NON_DISCRIMINATIVE'}
            continue
        logic, io = [], []
        for ref, r in cat.items():
            if not r['discriminative']:
                continue
            c = compare(d, r)
            if c == 'logic':
                logic.append(ref)
            elif c == 'io':
                io.append(ref)
        if logic:
            result[name] = {'outcome': 'SAME_LOGIC', 'refs': sorted(logic)}
        elif io:
            result[name] = {'outcome': 'SAME_FUNCTION', 'refs': sorted(io)}
        else:
            result[name] = {'outcome': 'NO_MATCH'}
    return result


def main():
    global EMPTY_TRACE
    cmd = sys.argv[1]
    if cmd == 'learn':
        learn(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        cat = json.loads(Path(sys.argv[3]).read_text(encoding='utf-8'))
        import hashlib  # noqa: F401
        for name, r in identify(Path(sys.argv[2]), cat).items():
            refs = r.get('refs', [])
            print(f"{name}: {r['outcome']} {len(refs)} refs: " + ', '.join(refs[:6]))


if __name__ == '__main__':
    main()

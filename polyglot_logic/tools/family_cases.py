#!/usr/bin/env python3
"""AP13 v3: check the family tree on the small own cases (examples/v3/expected_families.json).

correct  = some returned path equals the expected path
broader  = a returned path is a proper prefix of it (true, less specific)
wrong    = a returned path contradicts it
none     = no family
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from env_run import ROOT, ToolError  # noqa: E402
from family_scan import families  # noqa: E402

CASES = ROOT / 'examples' / 'v3'


def grade(expected, paths):
    if any(p == expected for p in paths):
        return 'correct'
    if any(p != expected and expected[:len(p)] == p for p in paths) and \
            not any(expected[:len(p)] != p for p in paths):
        return 'broader'
    return 'wrong' if paths else 'none'


def main() -> int:
    truth = {k: v for k, v in json.loads((CASES / 'expected_families.json').read_text()).items()
             if not k.startswith('_')}
    counts = {}
    for rel, expected in truth.items():
        try:
            fams = families(CASES / rel)
        except ToolError as exc:
            print(f'ERROR {rel}: {str(exc)[:300]}')
            counts['error'] = counts.get('error', 0) + 1
            continue
        paths = [p for ps in fams.values() for p in ps]
        g = grade(expected, paths)
        counts[g] = counts.get(g, 0) + 1
        got = ' | '.join('>'.join(p) for p in paths) or '-'
        print(f"{g:8s} {rel:28s} expected={'>'.join(expected)}  got={got}")
    print('AP13_FAMILY_CASES: ' + ' '.join(f'{k}={v}' for k, v in sorted(counts.items())))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

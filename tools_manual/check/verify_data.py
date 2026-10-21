"""Check that the frozen data is exactly what the results were measured on: every file in data/MANIFEST.sha256 (the
TheAlgorithms and Rosetta copies, and the Rosetta task labels; not data/README.md) is present with the same sha256, and no file was added.
usage: python tools_manual/check/verify_data.py          (exit 0 only when everything matches)
       python tools_manual/check/verify_data.py --write  (regenerate the manifest; only for a new, separately measured data set)"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'data' / 'MANIFEST.sha256'
EXTRA = ['polyglot_logic/benchmark/rosetta_truth.json']     # the task labels the held-out files are scored against


def files():
    out = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'data').rglob('*') if p.is_file() and p not in (MANIFEST, ROOT / 'data' / 'README.md'))
    return out + EXTRA


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def main():
    if '--write' in sys.argv:
        MANIFEST.write_text(''.join(f'{sha(f)}  {f}\n' for f in files()), encoding='utf-8')
        print('wrote', MANIFEST, len(files()), 'files')
        return 0
    want = dict(line.split('  ', 1)[::-1] for line in MANIFEST.read_text(encoding='utf-8').splitlines() if line)
    have = set(files())
    missing = sorted(set(want) - have)
    extra = sorted(have - set(want))
    changed = sorted(f for f in set(want) & have if sha(f) != want[f])
    for name, xs in (('missing', missing), ('changed', changed), ('extra', extra)):
        for x in xs:
            print(name, x)
    ok = not (missing or extra or changed)
    print(f"{len(want)} files: {'all match the tested data' if ok else 'DIFFERENT from the tested data'}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

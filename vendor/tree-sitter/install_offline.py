"""Install tree-sitter exactly as this project was tested, with no internet.

  1. pip installs tree-sitter 0.26.0 and tree-sitter-language-pack 1.22.1 from the wheels in wheels/.
  2. The 8 grammars the project uses (c, commonlisp, haskell, java, prolog, python, r, rust), prebuilt for this
     computer, are copied from parsers/<platform>/ into the language pack's cache folder.
  3. Each copied file is checked against SHA256SUMS, and each grammar is loaded once.

usage (from the repository root):  python vendor/tree-sitter/install_offline.py
"""
from __future__ import annotations

import hashlib
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LANGS = ['c', 'commonlisp', 'haskell', 'java', 'prolog', 'python', 'r', 'rust']
PINS = ['tree-sitter==0.26.0', 'tree-sitter-language-pack==1.22.1']


def this_platform() -> str:
    machine = platform.machine().lower()
    arch = 'arm64' if machine in ('arm64', 'aarch64') else 'x86_64'
    if sys.platform.startswith('win'):
        return 'windows-x86_64'
    if sys.platform == 'darwin':
        return f'macos-{arch}'
    return 'linux-x86_64'


def main() -> int:
    plat = this_platform()
    src = HERE / 'parsers' / plat
    if not src.is_dir():
        print(f'No prebuilt grammars for {plat}. Use the online install instead (see the root README).')
        return 1
    print(f'1/3 installing {", ".join(PINS)} from {HERE / "wheels"}')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-index', '--find-links', str(HERE / 'wheels'), *PINS],
                   check=True)
    import tree_sitter_language_pack as pack
    cache = Path(pack.cache_dir())
    cache.mkdir(parents=True, exist_ok=True)
    sums = dict(reversed(line.split(maxsplit=1)) for line in (HERE / 'SHA256SUMS').read_text().splitlines())
    print(f'2/3 copying the {plat} grammars into {cache}')
    for f in sorted(src.iterdir()):
        want = sums[f'./parsers/{plat}/{f.name}']
        got = hashlib.sha256(f.read_bytes()).hexdigest()
        if got != want:
            print(f'checksum mismatch: {f}')
            return 1
        shutil.copy2(f, cache / f.name)
    print('3/3 loading each grammar')
    for lang in LANGS:
        pack.get_parser(lang)
    print('done: tree-sitter is installed exactly as tested, for', ', '.join(LANGS))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

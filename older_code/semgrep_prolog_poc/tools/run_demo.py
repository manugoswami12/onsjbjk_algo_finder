#!/usr/bin/env python3
"""Run Python -> Semgrep OCaml generic AST -> JSON -> Prolog facts -> SWI-Prolog.

--ast-json replays a REAL previously captured Semgrep AST, for reproducibility.
Does not use Python's ast module, Semgrep match patterns, or external Python libs.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', nargs='?', default='examples/search_binary.py')
    ap.add_argument('--ast-json', type=pathlib.Path,
                    help='Replay an existing Semgrep dump-ast JSON instead of running Semgrep')
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument('--multi', action='store_true',
                       help='AP3: enumerate all recognized algorithm regions and strict order')
    modes.add_argument('--threads', action='store_true',
                       help='AP6: trace interleaved bubble-sort and rolling-hash logic threads')
    modes.add_argument('--audit', action='store_true',
                       help='AP8: opt-in conservative structural audit; AP7 modes unchanged')
    args = ap.parse_args()
    source = pathlib.Path(args.source)
    if not source.is_absolute():
        source = ROOT / source
    replay = args.ast_json
    if replay is not None:
        replay = replay.resolve()
        if not replay.is_file():
            print(f'ERROR: saved Semgrep AST not found: {replay}', file=sys.stderr)
            return 2
    elif not source.is_file():
        print(f'ERROR: source not found: {source}', file=sys.stderr)
        return 2
    executables = ('swipl',) if replay is not None else ('semgrep', 'swipl')
    for exe in executables:
        if shutil.which(exe) is None:
            print(f'ERROR: {exe} not on PATH (see README.md)', file=sys.stderr)
            return 2

    out = ROOT / 'out'
    out.mkdir(exist_ok=True)
    ast_json = out / 'ast.json'
    facts = out / 'facts.pl'
    # Never misinterpret an old candidate if a new invocation fails.
    for file in (ast_json, facts):
        if replay is None or file.resolve() != replay:
            file.unlink(missing_ok=True)

    try:
        if replay is None:
            print('1. Parsing with Semgrep OCaml generic AST...', flush=True)
            env = dict(os.environ, SEMGREP_SEND_METRICS='off')
            command = ['semgrep', 'show', 'dump-ast', '--json', str(source)]
            with ast_json.open('w', encoding='utf-8') as fh:
                result = subprocess.run(command, stdout=fh, stderr=subprocess.PIPE,
                                        text=True, timeout=60, env=env, check=False)
            if result.returncode:
                print(f'ERROR: Semgrep AST export failed: {result.stderr}', file=sys.stderr)
                ast_json.unlink(missing_ok=True)
                return result.returncode
        else:
            print('1. Replaying captured Semgrep OCaml AST...', flush=True)
            if replay != ast_json.resolve():
                shutil.copyfile(replay, ast_json)

        print('2. Exporting generic AST nodes and edges into Prolog...', flush=True)
        result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'export_ast_facts.py'),
                                 str(ast_json), str(facts)], timeout=30, check=False)
        if result.returncode:
            facts.unlink(missing_ok=True)
            return result.returncode
        if not facts.is_file() or not facts.stat().st_size:
            print('ERROR: empty Prolog fact output', file=sys.stderr)
            return 2

        print('3. Asking SWI-Prolog to identify algorithm candidate...', flush=True)
        if args.audit:
            rule_file, goal = 'audit_classify.pl', 'main_audit'
        elif args.threads:
            rule_file, goal = 'thread_classify.pl', 'main_threads'
        elif args.multi:
            rule_file, goal = 'multi_classify.pl', 'main_multi'
        else:
            rule_file, goal = 'classify.pl', 'main'
        command = ['swipl', '-q', '-f', 'none', '-s', str(ROOT / 'prolog' / rule_file),
                   '-s', str(facts), '-g', goal, '-t', 'halt']
        return subprocess.run(command, timeout=60, check=False).returncode
    except subprocess.TimeoutExpired as exc:
        print(f'ERROR: external command timed out: {exc.cmd}', file=sys.stderr)
        return 124
    except OSError as exc:
        print(f'ERROR: I/O or subprocess failure: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

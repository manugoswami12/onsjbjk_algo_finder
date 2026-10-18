#!/usr/bin/env python3
"""AP9 CLI: compile labeled reference once, match arbitrary Semgrep AST dumps."""
from __future__ import annotations
import argparse
import pathlib
import os
import shutil
import subprocess
import sys
from reference_pattern import compile_candidates, compile_reference, REGIONS
from typed_ast_codec import strict_load, typed_lines, decode_typed, json_text

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('reference_json', type=pathlib.Path, help='Semgrep JSON capture or Python .py source')
    ap.add_argument('target_json', type=pathlib.Path, help='Semgrep JSON capture or Python .py source')
    ap.add_argument('--label', required=True)
    ap.add_argument('--function', required=True)
    ap.add_argument('--region', choices=REGIONS, default='body')
    ap.add_argument('--ordinal', type=int, default=0)
    ap.add_argument('--out-dir', type=pathlib.Path, default=ROOT / 'out' / 'ap9')
    ap.add_argument('--offline-only', action='store_true',
                    help='Generate and validate facts/patterns, do not invoke SWI-Prolog')
    args = ap.parse_args()
    try:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        def resolve_capture(original, label):
            if not original.is_file():
                raise ValueError(f'missing input: {original}')
            if original.suffix.lower() != '.py':
                return original
            if not shutil.which('semgrep'):
                raise ValueError('semgrep not on PATH; required to parse Python .py source')
            capture = args.out_dir / (label + '_semgrep_ast.json')
            cmd = ['semgrep', 'show', 'dump-ast', '--json', str(original)]
            env = dict(os.environ, SEMGREP_SEND_METRICS='off')
            with capture.open('w', encoding='utf8') as fh:
                result = subprocess.run(cmd, stdout=fh, stderr=subprocess.PIPE,
                                        text=True, env=env, timeout=90, check=False)
            if result.returncode:
                capture.unlink(missing_ok=True)
                raise ValueError(f'Semgrep {label} AST export failed: {result.stderr}')
            strict_load(capture)
            return capture
        reference_capture = resolve_capture(args.reference_json, 'reference')
        target_capture = resolve_capture(args.target_json, 'target')
        typed = args.out_dir / 'typed_reference_facts.pl'
        tree = strict_load(reference_capture)
        lines = typed_lines(tree)
        if json_text(decode_typed(lines)) != json_text(tree):
            raise ValueError('typed JSON roundtrip mismatch')
        typed.write_text('\n'.join(lines) + '\n', encoding='utf8')
        meta = compile_reference(reference_capture, args.label, args.function,
                                 args.region, args.ordinal, args.out_dir / 'reference.pl')
        count = compile_candidates(target_capture, (args.region,), args.out_dir / 'candidate.pl')
        print(f'JSON_VALUE_ROUNDTRIP: PASS; reference={meta}; candidate_regions={count}', flush=True)
        if args.offline_only:
            print('OFFLINE_ONLY: Prolog recognition NOT RUN')
            return 0
        if not shutil.which('swipl'):
            print('ERROR: swipl not on PATH; recognition NOT RUN', file=sys.stderr)
            return 2
        cmd = ['swipl', '-q', '-f', 'none', '-s', str(ROOT / 'prolog' / 'reference_match.pl'),
               '-s', str(args.out_dir / 'reference.pl'),
               '-s', str(args.out_dir / 'candidate.pl'),
               '-g', 'main_reference', '-t', 'halt']
        return subprocess.run(cmd, check=False, timeout=120).returncode
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f'ERROR: AP9 runner: {exc}', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())

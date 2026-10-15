#!/usr/bin/env python3
"""AP9 evidence-based TP/FP/FN/TN evaluation on declared AST captures.

Use --backend prolog for the real SWI run. The optional Python oracle is only
an independent *offline structural-contract preflight*, not Prolog validation.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from reference_pattern import (Binding, REGIONS, compile_candidates,
                               compile_reference, declared_names,
                               functions, project_region, references, select_regions)
from typed_ast_codec import strict_load

ROOT = pathlib.Path(__file__).resolve().parents[1]


def unify_oracle(reference, target, bindings=None, inverse=None):
    """Reference-side alpha variables unify with target-side *ground* slots."""
    bindings = {} if bindings is None else bindings
    inverse = {} if inverse is None else inverse
    if isinstance(reference, Binding):
        if not isinstance(target, Binding): return False
        a, b = reference.name, target.name
        if a in bindings: return bindings[a] == b
        if b in inverse: return False
        bindings[a] = b
        inverse[b] = a
        return True
    if type(reference) is not type(target): return False
    if isinstance(reference, dict):
        return (list(reference) == list(target) and
                all(unify_oracle(v, target[k], bindings, inverse) for k, v in reference.items()))
    if isinstance(reference, list):
        return (len(reference) == len(target) and
                all(unify_oracle(v, w, bindings, inverse) for v, w in zip(reference, target)))
    return reference == target


def collect_projected(tree, kind):
    for _, name, params, body in functions(tree):
        binders = declared_names(params, body)
        for path, node in select_regions(body, kind):
            yield name, path, project_region(node, binders)


def detect_oracle(reference_tree, ref_function, region, ordinal, candidate_tree):
    """Standalone conformance oracle; NOT a replacement for SWI-Prolog."""
    ref_functions = [f for f in functions(reference_tree) if f[1] == ref_function]
    if len(ref_functions) != 1: raise ValueError('ambiguous reference function')
    _, _, params, body = ref_functions[0]
    selected = list(select_regions(body, region))
    if not 0 <= ordinal < len(selected): raise ValueError('invalid reference region ordinal')
    ref = project_region(selected[ordinal][1], declared_names(params, body))
    return {name for name, _, cand in collect_projected(candidate_tree, region)
            if unify_oracle(ref, cand)}


def safe_ident(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value))


def evaluate(manifest, backend='prolog'):
    path = pathlib.Path(manifest)
    dataset = json.loads(path.read_text(encoding='utf8'))
    ref_specs = dataset['references']
    cases = dataset['cases']
    if backend == 'prolog' and not shutil.which('swipl'):
        raise RuntimeError('swipl not on PATH: no Prolog validation performed')
    refs = {}
    for r in ref_specs:
        label = r['label']
        if not safe_ident(label) or label in refs:
            raise ValueError('reference labels must be unique simple identifiers')
        ref_path = (path.parent / r['ast_json']).resolve()
        ref_tree = strict_load(ref_path)
        refs[label] = (ref_tree, r['function'], r.get('region', 'body'), r.get('ordinal', 0), ref_path)
        # Reject malformed reference selectors early, before scoring.
        references(ref_tree, label, r['function'], r.get('region', 'body'), r.get('ordinal', 0))
    counts = dict(TP=0, FP=0, FN=0, TN=0)
    details = []
    with tempfile.TemporaryDirectory(prefix='ap9_eval_') as temp:
        tmp = pathlib.Path(temp)
        ref_file = tmp / 'refs.pl'
        clauses = ['% AP9 user-labeled references']
        for label, (tree, fn, region, ordinal, _) in refs.items():
            clause, _ = references(tree, label, fn, region, ordinal)
            clauses.append(clause)
        ref_file.write_text('\n'.join(clauses) + '\n', encoding='utf8')
        for case in cases:
            target = strict_load((path.parent / case['ast_json']).resolve())
            funcs = {name for _, name, _, _ in functions(target)}
            if not funcs: raise ValueError(f'case {case["id"]}: no functions')
            expected = {(entry['label'], entry['function']) for entry in case.get('expected', [])}
            if any(label not in refs or function not in funcs for label, function in expected):
                raise ValueError(f'case {case["id"]}: expected pair has unknown label/function')
            if backend == 'python_oracle':
                detected = set()
                for label, (ref_tree, ref_name, kind, ord_, _) in refs.items():
                    detected.update((label, function) for function in detect_oracle(
                        ref_tree, ref_name, kind, ord_, target))
            else:
                candidate_file = tmp / 'candidate.pl'
                compile_candidates((path.parent / case['ast_json']).resolve(), REGIONS, candidate_file)
                cmd = ['swipl', '-q', '-f', 'none', '-s', str(ROOT/'prolog'/'reference_match.pl'),
                       '-s', str(ref_file), '-s', str(candidate_file),
                       '-g', 'main_reference_machine', '-t', 'halt']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode or result.stderr.strip():
                    raise RuntimeError(f'Prolog case {case["id"]} failed: {result.stderr or result.stdout}')
                detected = set()
                for line in result.stdout.splitlines():
                    if not line.startswith('AP9MATCH|'): continue
                    parts = line.split('|', 3)
                    if len(parts) != 4: raise RuntimeError('malformed Prolog output')
                    _, label, function, _region = parts
                    detected.add((label, function))
            for label in refs:
                for func in funcs:
                    key = (label, func)
                    state = ('TP' if key in expected and key in detected else
                             'FN' if key in expected else
                             'FP' if key in detected else 'TN')
                    counts[state] += 1
            details.append({'id': case['id'], 'expected': sorted(map(list, expected)),
                            'detected': sorted(map(list, detected)),
                            'correct': expected == detected})
    tp, fp, fn = counts['TP'], counts['FP'], counts['FN']
    return {'backend': backend, 'counts': counts,
            'precision': tp/(tp+fp) if tp+fp else None,
            'recall': tp/(tp+fn) if tp+fn else None,
            'all_expected_results_match': all(x['correct'] for x in details),
            'cases': details,
            'disclaimer': 'bounded structural equivalence test; NOT universal semantic zero-error proof'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('manifest', type=pathlib.Path)
    ap.add_argument('--backend', choices=('prolog', 'python_oracle'), default='prolog')
    ap.add_argument('--out', type=pathlib.Path)
    args = ap.parse_args()
    try:
        result = evaluate(args.manifest, args.backend)
        txt = json.dumps(result, indent=2)
        print(txt)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(txt + '\n', encoding='utf8')
        return 0 if result['all_expected_results_match'] else 1
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f'ERROR: evaluation NOT completed: {exc}', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())

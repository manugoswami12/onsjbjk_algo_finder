"""Run source-only fallback pilot. NEVER imports or executes the analysed source."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from static_trace import analyze_source

ROOT = Path(__file__).resolve().parent
ROUTER = ROOT / 'prolog' / 'route.pl'


def facts_from(analyses):
    lines = ['% Derived solely from Python ast, no source execution.']
    # SWI-Prolog expects every clause of a predicate to be contiguous in a
    # consulted file. Emit all program/2 facts first, then all observed/3
    # facts. Interleaving by function triggers discontiguous warnings when a
    # real repository file contains more than one function.
    for i, _ in enumerate(analyses, 1):
        lines.append(f'program(f{i}, anonymous).')
    for i, analysis in enumerate(analyses, 1):
        ident = 'f' + str(i)
        for fact, positions in sorted(analysis.evidence.items()):
            # fact names are fixed by our code, not taken from source text
            for line in sorted(positions):
                lines.append(f'observed({ident}, {fact}, {line}).')
    return '\n'.join(lines) + '\n'


def route_live(analyses):
    swipl = shutil.which('swipl')
    if not swipl:
        raise RuntimeError('SWI-Prolog executable swipl is missing from PATH')
    with tempfile.TemporaryDirectory(prefix='algo_io_poc_') as td:
        facts_file = Path(td) / 'facts.pl'
        facts_file.write_text(facts_from(analyses), encoding='utf-8')
        # -s loads clauses but does NOT run main. Without -g main, SWI-Prolog
        # can wait for the user's console input until the 25s timeout.
        # -- separates Prolog options from the facts path read via argv.
        command = [swipl, '-q', '-s', str(ROUTER), '-g', 'main',
                   '-t', 'halt', '--', str(facts_file)]
        try:
            proc = subprocess.run(command, stdin=subprocess.DEVNULL,
                                  text=True, capture_output=True, timeout=25)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('SWI-Prolog did not exit after running main '
                               '(25-second timeout)') from exc
        if proc.returncode != 0 or proc.stderr.strip():
            raise RuntimeError(f'Prolog routing failed: {proc.stderr or proc.stdout}')
        routes = {f'f{i}': [] for i in range(1, len(analyses) + 1)}
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) != 3 or parts[0] != 'ROUTE' or parts[1] not in routes:
                raise RuntimeError('Unexpected Prolog output: ' + line)
            routes[parts[1]].append(parts[2])
        for identifier, values in routes.items():
            if not values:
                raise RuntimeError('SWI-Prolog produced no ROUTE for ' + identifier)
        return routes


def load(path):
    path = Path(path)
    if path.stat().st_size > 1_000_000:
        raise ValueError('Input too large for this bounded pilot (1 MB limit)')
    return analyze_source(path.read_text(encoding='utf-8-sig'))


def selftest(offline=False):
    cases = [
        ('bubble.py', {'sequence_rearrangement', 'comparison_driven_reordering'}),
        ('reverse.py', {'sequence_rearrangement'}),
        ('binary.py', {'indexed_lookup', 'interval_lookup'}),
        ('linear.py', {'indexed_lookup'}),
        ('unrelated_compare.py', {'unknown'}),
        ('unrelated_array.py', {'sequence_rearrangement'}),
        ('fake_midpoint.py', {'unknown'}),
        ('dead_swap.py', {'unknown'}),
        ('wrong_exchange.py', {'unknown'}),
        ('mixed.py', {'comparison_driven_reordering', 'sequence_rearrangement',
                      'indexed_lookup', 'interval_lookup'}),
        ('unknown_call.py', {'unknown'}),
    ]
    passed = 0
    for case, expected in cases:
        analyses = load(ROOT / 'examples' / case)
        if len(analyses) != 1:
            raise AssertionError(case + ': expected one function')
        facts = set(analyses[0].evidence)
        display_routes = '(offline: Prolog not run)'
        if offline:
            # No duplicate Python routing implementation: validate evidence only.
            required = {
                'comparison_driven_reordering': 'comparison_controls_exchange',
                'sequence_rearrangement': 'element_exchange',
                'indexed_lookup': 'indexed_equality_controls_index_return',
                'interval_lookup': 'coherent_midpoint_interval_update',
            }
            for route, evidence in required.items():
                if (route in expected) != (evidence in facts):
                    raise AssertionError(case + ': incorrect static evidence: ' + evidence)
        else:
            actual = set(route_live(analyses)['f1'])
            if actual != expected:
                raise AssertionError(f'{case}: expected {sorted(expected)}, got {sorted(actual)}')
            display_routes = ','.join(sorted(actual))
        passed += 1
        print('PASS', case, 'routes=' + display_routes, 'facts=' + ','.join(sorted(facts)))
    print(f'POC {"STATIC" if offline else "SWI-PROLOG LIVE"} ACCEPTANCE: {passed}/{len(cases)} PASS')


def main():
    p = argparse.ArgumentParser(description='Standalone static input/output branch-routing pilot')
    p.add_argument('source', nargs='?', help='Python source file; never executed')
    p.add_argument('--selftest', action='store_true')
    p.add_argument('--offline-tests', action='store_true', help='Only static extraction, no Prolog')
    p.add_argument('--json', action='store_true', help='Print observations as JSON')
    args = p.parse_args()
    if args.selftest or args.offline_tests:
        selftest(offline=args.offline_tests)
        return
    if not args.source:
        p.error('Pass a source file or --selftest')
    analyses = load(args.source)
    if not analyses:
        print('UNKNOWN: no top-level functions found')
        return
    routes = route_live(analyses)
    for i, a in enumerate(analyses, 1):
        report = {'function': a.name, 'input_parameters': a.inputs,
                  'output_observations': a.outputs,
                  'may_depend_on': a.dependencies,
                  'evidence_lines': a.evidence, 'limitations': a.unknowns,
                  'candidate_routes': routes['f'+str(i)]}
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print('\nFUNCTION:', a.name)
            print('INPUTS:', ', '.join(a.inputs))
            print('OUTPUT:', '; '.join(a.outputs) or 'No explicit return')
            for name, positions in sorted(a.evidence.items()):
                print('OBSERVED:', name, 'lines', ','.join(map(str, sorted(positions))))
            if a.unknowns:
                print('LIMITATIONS:', '; '.join(a.unknowns))
            print('CANDIDATE BRANCHES:', ', '.join(routes['f'+str(i)]))
            print('NOT A PROOF OF ALGORITHM IDENTITY OR CORRECTNESS')


if __name__ == '__main__':
    try:
        main()
    except (OSError, SyntaxError, ValueError, RuntimeError, AssertionError,
            subprocess.TimeoutExpired) as exc:
        print('POC ERROR:', exc, file=sys.stderr)
        sys.exit(1)

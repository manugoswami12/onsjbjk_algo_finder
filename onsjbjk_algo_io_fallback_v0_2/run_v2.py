"""v0.2 source-only fallback runner (from run_poc.py). NEVER imports or executes the analysed source."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from static_trace_v2 import analyze_source

ROOT = Path(__file__).resolve().parent
ROUTER = ROOT / 'prolog' / 'route_v2.pl'


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
    with tempfile.TemporaryDirectory(prefix='algo_io_v02_') as td:
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


# v0.1 acceptance cases, unchanged: (file, expected routes)
V01_CASES = [
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

# v0.2 cases: (file, expected routes, evidence that must be observed offline)
SORTED = {'sequence_rearrangement', 'comparison_driven_reordering'}
V02_CASES = [
    ('insertion.py', SORTED | {'shift_insertion'}, {'adjacent_shift_write', 'comparison_controls_shift'}),
    ('selection.py', SORTED | {'selection_exchange'}, {'element_exchange', 'min_index_then_exchange'}),
    ('sum_list.py', {'aggregate', 'element_accumulation'}, {'input_element_accumulated'}),
    ('max_list.py', {'aggregate', 'extremum_search'}, {'best_so_far_update'}),
    ('membership.py', {'membership_lookup'}, {'element_equality_controls_true_return'}),
    ('fib_iter.py', {'recurrence', 'fibonacci_like'}, {'pair_recurrence'}),
    ('fib_rec.py', {'recurrence', 'fibonacci_like', 'recursive_decomposition'},
     {'double_self_call', 'self_calls_minus_one_minus_two'}),
    ('gcd_loop.py', {'recurrence', 'euclid_like'}, {'modulo_recurrence'}),
    ('gcd_rec.py', {'recurrence', 'euclid_like'}, {'modulo_recurrence'}),
    ('factorial_loop.py', {'recurrence', 'factorial_like'}, {'range_product'}),
    ('factorial_rec.py', {'recurrence', 'factorial_like'}, {'linear_self_product'}),
    ('sum_range.py', {'recurrence', 'series_sum'}, {'range_sum'}),
    ('digit_sum.py', {'number_property', 'digit_processing'}, {'digit_decomposition'}),
    ('is_prime.py', {'number_property', 'divisor_search'}, {'divisor_test_in_loop'}),
    ('collatz.py', {'number_property', 'collatz_like'}, {'parity_halving_or_triple'}),
    ('sieve.py', {'marking', 'sieve_like'}, {'stride_marking', 'flag_guards_stride'}),
    ('palindrome.py', {'symmetric_compare', 'palindrome_check'}, {'mirror_compare', 'mirror_compare_decides_result'}),
    ('palindrome_slice.py', {'symmetric_compare', 'palindrome_check'}, {'mirror_compare_decides_result'}),
    # near misses: UNKNOWN or the broad branch only
    ('accum_constant.py', {'unknown'}, set()),
    ('fake_pair.py', {'unknown'}, set()),
    ('mod_once.py', {'unknown'}, set()),
    ('stride_no_write.py', {'unknown'}, set()),
    ('shift_no_compare.py', {'sequence_rearrangement'}, {'adjacent_shift_write'}),
    ('mirror_unrelated.py', {'unknown'}, set()),
    ('max_not_returned.py', {'unknown'}, set()),
]

V01_ONLY_FACTS = {'returned_input'}


def selftest(offline=False):
    """One SWI-Prolog call for all cases (cheap); offline checks static evidence only."""
    cases = [(c, e, None) for c, e in V01_CASES] + V02_CASES
    analyses = []
    for case, _, _ in cases:
        found = load(ROOT / 'examples' / case)
        if len(found) != 1:
            raise AssertionError(case + ': expected one function')
        analyses.append(found[0])
    routes = None if offline else route_live(analyses)
    required_v01 = {
        'comparison_driven_reordering': 'comparison_controls_exchange',
        'sequence_rearrangement': 'element_exchange',
        'indexed_lookup': 'indexed_equality_controls_index_return',
        'interval_lookup': 'coherent_midpoint_interval_update',
    }
    passed = 0
    for i, ((case, expected, must), analysis) in enumerate(zip(cases, analyses), 1):
        facts = set(analysis.evidence)
        display_routes = '(offline: Prolog not run)'
        if offline:
            # No duplicate Python routing implementation: validate evidence only.
            if must is None:
                for route, evidence in required_v01.items():
                    if (route in expected) != (evidence in facts):
                        raise AssertionError(case + ': incorrect static evidence: ' + evidence)
                if facts - V01_ONLY_FACTS - set(required_v01.values()) - {'input_sequence_mutated'}:
                    raise AssertionError(case + ': v0.2 witness fired on a v0.1 case: ' + ','.join(sorted(facts)))
            elif expected == {'unknown'}:
                if facts - V01_ONLY_FACTS:
                    raise AssertionError(case + ': near miss produced evidence: ' + ','.join(sorted(facts)))
            elif not must <= facts:
                raise AssertionError(f'{case}: missing evidence {sorted(must - facts)}')
        else:
            actual = set(routes['f' + str(i)])
            if actual != expected:
                raise AssertionError(f'{case}: expected {sorted(expected)}, got {sorted(actual)}')
            display_routes = ','.join(sorted(actual))
        passed += 1
        print('PASS', case, 'routes=' + display_routes, 'facts=' + ','.join(sorted(facts)))
    print(f'V0.2 {"STATIC" if offline else "SWI-PROLOG LIVE"} ACCEPTANCE: {passed}/{len(cases)} PASS')


def main():
    p = argparse.ArgumentParser(description='v0.2 static input/output branch routing (logic trace, I/O fallback)')
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
            if routes['f'+str(i)] == ['unknown']:
                # Fallback: no logic branch is supported, report input->output dependence only.
                print('IO FALLBACK:', '; '.join(a.outputs) or 'no explicit output')
            print('NOT A PROOF OF ALGORITHM IDENTITY OR CORRECTNESS')


if __name__ == '__main__':
    try:
        main()
    except (OSError, SyntaxError, ValueError, RuntimeError, AssertionError,
            subprocess.TimeoutExpired) as exc:
        print('V0.2 ERROR:', exc, file=sys.stderr)
        sys.exit(1)

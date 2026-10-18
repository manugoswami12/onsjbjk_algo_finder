# v0.2 static logic-trace router with I/O fallback: requirements and design

v0.2 is built by copying `onsjbjk_algo_io_fallback_poc_v0_1/`; the original folder and
all frozen AP/corpus code stay untouched. The copied v0.1 files (`static_trace.py`,
`run_poc.py`, `prolog/route.pl`, docs 01–03, 11 examples, tests) are kept unchanged,
so v0.1 behaviour is reproducible inside this folder. The method is exactly the POC's:

1. static logic tracing with Python `ast` (candidate source never imported or executed);
2. emit `observed(F, Fact, Line)` facts;
3. SWI-Prolog `route/2` from broad family to narrow branch;
4. input→output dependence as the fallback report;
5. `unknown` when the evidence is insufficient.

## 1. Requirements

| # | Requirement |
|---|---|
| R1 | Source only: stdlib `ast`; the analysed file is never imported, `exec`'d or run. |
| R2 | Every fact is a local, conservative witness tied to the function inputs (may-depend-on). |
| R3 | A route is a candidate branch, never a proof of algorithm identity or correctness. |
| R4 | Narrow branch = broad parent + extra evidence. Larger variations stay in the broad branch; acceptance is never relaxed to "catch more". |
| R5 | `unknown` when no broad family has evidence; then the input→output dependence is reported (I/O fallback). |
| R6 | All 11 v0.1 cases give exactly the v0.1 routes. |
| R7 | Each new branch has a positive example and the families have near-miss negatives. |
| R8 | Tools: Python 3 stdlib and SWI-Prolog only (no ML, no new packages, no network). |
| R9 | Windows: `ons_ruleskg` conda env, `A:\swipl\bin`, `.cmd` runners; SWI launched with `-g main -t halt`, stdin closed, 25 s timeout, any stderr is failure. |

## 2. Branch tree (broad → narrow)

```
sequence_rearrangement        (exchange | adjacent shift on an input sequence)
 └ comparison_driven_reordering   (compare controls exchange | compare controls shift | min-index then exchange)
     ├ shift_insertion
     └ selection_exchange
indexed_lookup → interval_lookup                      (v0.1, unchanged)
membership_lookup                                     (element == target controls `return True`)
aggregate                     (gatherer | best-so-far over input elements)
 ├ element_accumulation
 └ extremum_search
recurrence                    (input-driven recurrence)
 ├ fibonacci_like   (a,b = b,a+b | f(n-1)+f(n-2))
 ├ euclid_like      (a,b = b,a%b | t=a%b;a=b;b=t | f(b, a%b))
 ├ factorial_like   (acc *= i over range | n*f(n-1))
 └ series_sum       (acc += i over range)
recursive_decomposition       (two self-calls + base case; broad only)
number_property
 ├ digit_processing (n%10 with n//=10 in a while on n)
 ├ divisor_search   (n % d == 0, d a loop stepper)
 └ collatz_like     (parity test, n//2 and 3n+1 in a while on n)
marking → sieve_like          (strided constant writes; flag M[p] guards the stride)
symmetric_compare → palindrome_check   (A[i] vs A[mirror i] | two pointers | A == A[::-1]; decides the result)
unknown                       (no broad family)
```

## 3. Python pseudocode

```python
def analyse_v2(fn):
    result = analyse(fn)                 # v0.1: inputs, may-depend-on fixpoint, outputs, v0.1 facts
    rows = statements(fn.body)           # v0.1 walk: (stmt, guards, loops); dead `if False` skipped
    tainted = names whose dependencies include an input
    returned = names used by any return
    w_sorting(rows):    shift  A[x+1] = A[x] inside while            -> adjacent_shift_write
                        while test compares A[..]                      -> comparison_controls_shift
                        guarded m = j by A[j] <cmp> A[m], swap with A[m] -> min_index_then_exchange
    w_aggregate(rows):  acc op= v in a loop, acc returned
                          v element of input   -> input_element_accumulated
                          v range stepper      -> range_sum | range_product
                        best = v guarded by v <cmp> best, best returned -> best_so_far_update
    w_membership(rows): return True guarded by element == input target -> element_equality_controls_true_return
    w_recurrence(rows): (x,y) = (y, x+y) in input-driven loop, x|y returned -> pair_recurrence
                        (a,b) = (b, a%b) in while on b | 3-statement form | return f(b, a%b) -> modulo_recurrence
                        return n * f(n-1) with base case -> linear_self_product
                        two self-calls in one statement with base case -> double_self_call
                          args n-1, n-2 and `+` -> self_calls_minus_one_minus_two
    w_number(rows):     while on tainted n: n //= 10 and n % 10 -> digit_decomposition
                                            parity if, n//2, 3*n+1 -> parity_halving_or_triple
                        if n % d == 0 with d a loop stepper -> divisor_test_in_loop
    w_marking(rows):    for j in range(s, ..n.., p) inside for p: M[j] = const -> stride_marking
                        guard on M[p] -> flag_guards_stride
    w_mirror(rows):     mirror compare in if/return -> mirror_compare; decides bool return -> ..._decides_result
    return result

facts = program/2 for all functions, then observed/3     # v0.1 grouping fix (doc 03)
routes = swipl -q -s route_v2.pl -g main -t halt -- facts.pl
print report; if routes == [unknown]: print IO FALLBACK (return expression and its input dependence)
```

## 4. Activity classification (one program per type)

| Activity type | Program | Library |
|---|---|---|
| Parse and trace (walk, guards, loops, dependence fixpoint, v0.1 witnesses) | `static_trace.py` (copied, unchanged) | `ast`, `dataclasses` |
| New witnesses (one function per family) | `static_trace_v2.py` | `ast`, `re` |
| Fact emission, Prolog launch, report, selftest | `run_v2.py` (from `run_poc.py`) | `subprocess`, `tempfile`, `argparse`, `json` |
| Routing broad → narrow, unknown | `prolog/route_v2.pl` | SWI-Prolog |
| Windows runners | `RUN_FALLBACK_V02.cmd`, `RUN_STATIC_SELFTEST_V02.cmd` | cmd |
| Tests | `tests/test_v2.py` (+ copied v0.1 tests) | `unittest`, `unittest.mock` |

## 5. Critical-logic table

Critical means the logic talks to the environment or another program, or more than two other parts are built on it.

| Logic | Where | Why critical | Safeguard |
|---|---|---|---|
| `statements()` walk with guards/loops | `static_trace.py` | base of every witness | unchanged v0.1 code; dead-code test |
| may-depend-on fixpoint → `tainted_names` | `static_trace.py`, `static_trace_v2.py` | ties every v0.2 witness to inputs (R2) | bounded 16 iterations; negative tests |
| `returned_names` | `static_trace_v2.py` | base of aggregate/recurrence witnesses | `max_not_returned.py` negative |
| fact emission order | `run_v2.py:facts_from` | interface to SWI-Prolog | program/2 then observed/3 (doc 03); tests |
| SWI launch | `run_v2.py:route_live` | interface to environment | `-g main -t halt`, DEVNULL, timeout, stderr = error; mock test |
| `route(F, unknown)` over `broad/1` | `route_v2.pl` | decides fallback for every function | every broad family listed; near-miss cases |
| v0.1 rules | `route_v2.pl` | base of sorting/lookup branches | copied verbatim; 11 v0.1 cases |

## 6. Problems table

| Problem | Effect | Handling in v0.2 |
|---|---|---|
| Aliasing (`b = a` then mutate `b`) | witness may be missed | missed = `unknown`, never a wrong branch |
| Renamed builtins / helper calls | not interpreted | `unknown`; helpers never assumed |
| Several algorithms in one function | several branches | all reported (as v0.1 `mixed.py`) |
| Recursion with other shapes (mergesort, quicksort) | only `recursive_decomposition` | broad only by design (R4) |
| Euclid / Fibonacci in other syntactic forms | missed | listed forms only; extend with new witnesses, never loosen |
| Nested defs, try/with/match, eval/exec | not traversed | recorded as LIMITATIONS (v0.1) |
| Over-generalisation ("everything becomes bubble sort") | false branches | each witness needs input tie + specific operator; near-miss negatives in selftest |
| Only Python sources | other languages unrouted | out of scope for v0.2 |

## 7. Acceptance

`run_v2.py --selftest`: one SWI-Prolog call, 36 cases. These are the 11 v0.1 cases, unchanged, plus 18 v0.2 positives and 7 near-miss negatives. `--offline-tests` checks the static evidence without Prolog.

## 8. Established basis

- M. Weiser, *Program Slicing*, ICSE 1981; Ferrante, Ottenstein & Warren, *The Program Dependence Graph*, TOPLAS 1987. These give the input→output dependence and the input tie of every witness.
- J. Sajaniemi, *An Empirical Analysis of Roles of Variables*, 2002. The witnesses use these roles: stepper, gatherer, most-wanted holder, follower, one-way flag.
- A. Taherkhani et al., *Recognizing Algorithms Using Language Constructs, Software Metrics and Roles of Variables*, 2010–2013. Its decision tree over roles and beacons is the model for the broad→narrow routing.
- LLVM `ScalarEvolution`, which uses chains of recurrences (Bachmann, Wang & Zima 1994). This is the basis of the recurrence witnesses.
- LLVM `LoopIdiomRecognize`, which recognises memset/memcpy-like idioms. This is the basis of the shift and stride-marking witnesses.
- P. Ginsbach & M. O'Boyle, *Discovery and Exploitation of General Reductions*, CGO 2017. This is the basis of the accumulation and best-so-far witnesses.
- SWI-Prolog, used for the routing rules.

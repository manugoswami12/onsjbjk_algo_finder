# v0.2 technical details (the former folder README; see the root README.md to run the project)

This code began as a copy of `onsjbjk_algo_io_fallback_poc_v0_1/` (now in `older_code/`), extended; that folder is not modified. The v0.1 files are kept unchanged here (`run_poc.py`, `static_trace.py`, `prolog/route.pl`, `RUN_FALLBACK_POC.cmd`). The v0.2 files sit next to them:

| File | Role |
|---|---|
| `static_trace_v2.py` | v0.1 analysis plus the new witnesses |
| `prolog/route_v2.pl` | v0.1 rules plus the new broad → narrow branches |
| `run_v2.py` | runner, report with the I/O fallback, 36-case selftest |
| `RUN_FALLBACK_V02.cmd`, `RUN_STATIC_SELFTEST_V02.cmd` | Windows runners |
| `docs/01_V02_REQUIREMENTS_DESIGN.md` | requirements, branch tree, pseudocode, classification, critical and problems tables |

The early v0.2 router is run from the repository root, with SWI-Prolog on PATH (see the root README):

```
RUN_FALLBACK_V02.cmd examples\sieve.py
RUN_STATIC_SELFTEST_V02.cmd
```

**Branches.** The v0.1 branches are unchanged:
- `sequence_rearrangement`, `comparison_driven_reordering`;
- `indexed_lookup`, `interval_lookup`.

v0.2 adds these, written as broad family → narrow branches:

| Broad family | Narrow branches |
|---|---|
| `comparison_driven_reordering` (from v0.1) | `shift_insertion`, `selection_exchange` |
| `membership_lookup` | none |
| `aggregate` | `element_accumulation`, `extremum_search` |
| `recurrence` | `fibonacci_like`, `euclid_like`, `factorial_like`, `series_sum` |
| `recursive_decomposition` | none |
| `number_property` | `digit_processing`, `divisor_search`, `collatz_like` |
| `marking` | `sieve_like` |
| `symmetric_compare` | `palindrome_check` |

When no family has evidence, the router answers `unknown` and the report prints `IO FALLBACK`, the input→output dependence of the returns.

These are candidate branches, not proofs of algorithm identity. Unknown source is never executed. No packages beyond Python 3 and SWI-Prolog are needed.

## Learning and final results

- `learn_v2.py`: new learner (AST normalisation + winnowing, nearest neighbour).
- `compare_learners.py`: v0.2 also uses the original AP13 learners from `polyglot_logic` (read-only):
  `learn-dir` (exact traced logic) and `io_catalog` (behaviour; runs a Prolog translation on fixed inputs).
- `eval_heldout.py <checkout> <truth.json> [--kb kb/learned.json] [--learner iocat --train T1.json ...]`

| Test (TheAlgorithms/Python, keys frozen first) | Precision | Recall |
|---|---|---|
| 15 files (used for fixes, not held-out) | 100% | 100% |
| 55 files, witnesses only | 81.8% | 47.4% |
| fresh 55, witnesses + io_catalog | 87.5% | 56.0% |
| **final 101, witnesses + io_catalog** | **66.7%** | **33.3%** |

See `benchmark/learner_comparison.md` and `benchmark/final101_result.md`.

## All of TheAlgorithms/Python (doc 04 section 17)

Every algorithm of TheAlgorithms/Python (commit e1a2a8b0) is learned from Python and then tested. A label that
learning gets wrong gets a hand-written rule, the same in every language:
- general relations in `prolog/ta_rules.pl`;
- file rules in `prolog/ta_file_rules.pl`.

The scripts:
- `ta_corpus.py`, `eval_ta.py` and `learn_apply.py` do the learning and testing;
- `ta_distinct.py` writes the file rules;
- `ta_prompts.py` writes one prompt per rule (`docs/RULE_PROMPTS.md`) for writing the same kind of rule in future.

Result: 1344 of the 1344 analysable files are identified (0 false positives, 0 false negatives). Two files with no
algorithm code are not scored, and files with identical logic count as one.

## Separate fallback for new code (doc 04 section 18; never loaded by the pipeline)

| File | Role |
|---|---|
| `prolog/class_specs.pl`, `ta_classes.py` | Class relations (sorting, search, gcd, lcm, factorial, Fibonacci, prime check, ...), checked on the program's runs on fixed inputs (`sum(2,3,X)` style). |
| `prolog/call_roots.pl`, `tools_manual/decide_new_or_known.py` | Decide on the file's root functions only. "New version of a known class" needs every root to run on every input, one relation to hold and a tree node. Otherwise the answer is "new or incorrect implementation", or undecided. |
| `tools_manual/write_branches.py`, `prolog/proposed_branches.pl`, `eval_proposed.py` | Each class decision on a TheAlgorithms file becomes a Prolog branch at its tree node: `proposed_branch(Node, Class) :- class_holds(Class).` |
| `prolog/library_names.pl`, `ta_library.py`, `eval_library.py` | A program whose whole computation is one library call is named by that library's algorithm. |
| `pnf_v03.py`, `prolog/interp_v03.pl`, `prolog/run_main_v03.pl` | v0.3 runner: AP13's lowerer and interpreter extended, not edited. It adds lambdas and closures, module-level constants, generator arguments, and `str`/`set`/`chain`/`zip`/`bisect`. |
| `eval_decision.py`, `final_report.py` | Give every held-out file an answer, and write `benchmark/FINAL_REPORT.md` under the reporting criteria. |

Results: 39 of 39 held-out class decisions are right, 14 of 14 branch firings are right, and all 37 class claims on
TheAlgorithms are right.

| New code (held-out Rosetta) | analysable files | precision | recall (analysable) | recall (all files) |
|---|---|---|---|---|
| C | 34 of 69 | 96.9% | 91.2% | 44.9% |
| Common Lisp | 46 of 75 | 97.8% | 95.7% | 58.7% |
| Haskell | 42 of 144 | 94.3% | 78.6% | 22.9% |
| Python | 83 of 162 | 93.0% | 79.5% | 40.7% |
| **all** | **205 of 450** | **95.1%** | **84.9%** | **38.7%** |

All 9 wrong answers on new code come from the main pipeline. The separate fallback made none.

To reproduce every number above, follow "Reproduce the results" in the root [README.md](../README.md).

Limits:
- **A class, not which algorithm.** A class relation says "sorting", not which sort.
- **A new algorithm cannot be told from an incorrect implementation.** Both are reported as "new or incorrect
  implementation".
- **Code that does not run on every input is not analysed.** This covers GHCi transcripts, fragments, missing
  packages, type errors, curried Python, and strings as character codes.
- **One implementation per algorithm to learn from.** New styles often land on broad tree nodes.

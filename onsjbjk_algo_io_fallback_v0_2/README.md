# Static logic-trace router with I/O fallback (v0.2)

This folder is a copy of `onsjbjk_algo_io_fallback_poc_v0_1/`, extended. The original folder is not modified. The v0.1 files are kept unchanged here (`run_poc.py`, `static_trace.py`, `prolog/route.pl`, `RUN_FALLBACK_POC.cmd`). The v0.2 files sit next to them:

| File | Role |
|---|---|
| `static_trace_v2.py` | v0.1 analysis plus the new witnesses |
| `prolog/route_v2.pl` | v0.1 rules plus the new broad → narrow branches |
| `run_v2.py` | runner, report with the I/O fallback, 36-case selftest |
| `RUN_FALLBACK_V02.cmd`, `RUN_STATIC_SELFTEST_V02.cmd` | Windows runners |
| `docs/01_V02_REQUIREMENTS_DESIGN.md` | requirements, branch tree, pseudocode, classification, critical and problems tables |

**Windows CMD:**

```cmd
conda activate ons_ruleskg
set "PATH=A:\swipl\bin;%PATH%"
cd /d <path>\onsjbjk_algo_io_fallback_v0_2
call RUN_FALLBACK_V02.cmd
call RUN_FALLBACK_V02.cmd examples\sieve.py
call RUN_STATIC_SELFTEST_V02.cmd
python -m unittest discover -s tests -v
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

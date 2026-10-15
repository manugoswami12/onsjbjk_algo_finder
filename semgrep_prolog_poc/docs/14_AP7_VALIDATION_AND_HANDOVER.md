# AP7 validation and handover (2026-10-09)

## Defect fixed

* User's Windows acceptance run: 58 tests, 9 failures, all caused by an absent `rolling_hash_update` classification (including all interleaving relationships). Prior AP5 bubble sort and binary search remained working.
* Source: `prolog/thread_rules.pl::block_statement_holding/3` used `Statement == Event` while `Event` was unbound. This expression cannot bind `Event` to an immediate `Block` child such as `Return`.
* Repair: `Event = Statement ; under(Statement, Event)` permits direct-child enumeration by unification, while retaining descendant matching. All other recognition predicates are unchanged.

## Change scope

* Modified: `prolog/thread_rules.pl` (one core operator plus explanatory comments).
* Modified: `tests/test_thread_recognition.py` (two focused regressions, one requiring SWI-Prolog).
* Added: `docs/13_AP7_FIX_REQUIREMENTS_AND_CRITICAL_LOGIC.md`, `docs/14_AP7_VALIDATION_AND_HANDOVER.md`.
* All other files from the user-supplied `ap6.zip` remain byte-identical. Existing example tests, exact AST export, CLI flags, AP2/AP5 rules and CMD runners remain intact.

## Tests run in this workspace

`python -m unittest discover -s tests -v`

Result: **60 tests total, 26 passed, 34 skipped, 0 failed.** The skipped 34 require SWI-Prolog and/or Semgrep, neither available here. The unification fix is logically consistent with the source AST, but **full runtime acceptance is not yet verified**.

## Office Windows instructions

Extract the ZIP into a NEW folder first; open CMD there, with your existing `ons_ruleskg` activated and your `swipl` PATH set. Run:

```cmd
RUN_AP6_ACCEPTANCE.cmd
RUN_THREADS.cmd examples\interleaved_sort_hash.py
RUN_THREADS.cmd examples\interleaved_no_swap.py
RUN_THREADS.cmd examples\interleaved_separate_functions.py
```

For acceptance: **60 tests, 0 failures, 0 skips** (assuming both tools available).

Expected results:
* Interleaved example: `bubble_sort` and `rolling_hash_update` with `INTERLEAVED_WITH` relation.
* No swap: rolling hash only; no bubble sort or interleaving.
* Separate functions: independently identified sorting and rolling hash; no cross-function interleaving.
* Wrong array or index: two algorithms may be identified but interleaving relation must be absent.
* Invalid multiplier/modulus, missing return, invalid accumulator recurrence, reset: no rolling hash.
* Existing AP5 binary-search and multi-region tests remain passing.

Do not treat a recognized structural candidate as an algorithm-correctness proof. Save a copy of the full Windows output for final freeze.

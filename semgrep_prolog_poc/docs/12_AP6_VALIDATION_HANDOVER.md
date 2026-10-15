# AP6 Validation / Handover

## Scope and provenance

Baseline: uploaded `ap5.zip` with Windows-verified 37/37 AP5 tests. AP6 only adds `prolog/thread_rules.pl`, `prolog/thread_classify.pl`, example cases, tests, documents, Windows and Linux launchers, and an opt-in `--threads` choice in `tools/run_demo.py`. Core exporter and AP5 predicate implementations remain unchanged.

## Primary source contract

Semgrep's *real* OCaml `AST_generic` JSON is exported with its full record and variant structure intact. New tests' `tests/thread_contract_ast.py` constructs **synthetic JSON structures**, not captured Semgrep output. The actual executable source must be parsed and accepted independently on the user's Windows PC.

## Two structurally connected threads

- Bubble: existing nested For + adjacent comparison + correctly reversed indexed swap.
- Rolling hash: `digest = 0` in outer function body; inside the sort inner loop `digest = (digest * 31 + items[j]) % 1000000007`; same `digest` returned after outer loop; no other writes to the digest variable. The array and index must coincide with the bubble-sort comparison/swap to claim interleaving.
- The positive example's digest captures the sequence of values encountered during comparisons. It is not necessarily a hash of the sorted array.
- Since `--threads` is opt-in, AP5's original outputs and query predicates remain available.

## How to run

From the extracted `semgrep_prolog_poc` folder in a **new Windows CMD** with existing `ons_ruleskg`, `swipl` and `semgrep` available:

```cmd
RUN_AP6_ACCEPTANCE.cmd
RUN_THREADS.cmd examples\interleaved_sort_hash.py
```

To test a different source: `RUN_THREADS.cmd <path_to_python_file>`.

## Acceptance evidence required

1. All AP5 tests and live AP5 demo outputs remain unchanged.
2. AP6 positive recognizes `bubble_sort`, `rolling_hash_update`, and exactly the intended `INTERLEAVED_WITH` link (with concrete function and AST regions).
3. Synthetic and live negative controls do not report unsupported thread combinations.
4. No SWI-Prolog warnings, no semgrep parse failure, no skipped tests on Windows.
5. If a failure occurs, preserve `out/ast.json`, `out/facts.pl`, the source, the first failing assertion, and the Semgrep version. Do NOT rewrite the exporter to mimic predicted AST output.

## Local development status

Builder environment lacks both `swipl` and `semgrep`. Offline Python tests can run, but live Semgrep→Prolog tests and actual `INTERLEAVED_WITH` success remain **unverified** until office acceptance. Synthetic contract tests are useful for regression but do not replace the full test.

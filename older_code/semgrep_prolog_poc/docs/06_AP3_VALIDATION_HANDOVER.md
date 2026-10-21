# AP3 validation and handover: two algorithm regions, one function

## What AP3 actually changes
- Preserves AP2's fact-export format, exact Semgrep JSON, captured real 783-node AST fixture, original `RUN_DEMO`, `RUN_SELFTESTS`, and Prolog `candidate/1` and `candidate/2`.
- Adds `--multi` to the existing runner, with `RUN_MULTI.cmd/.sh` entrypoints.
- Adds Prolog-only function/region navigation, nested-For/adjacent-parallel-swap matching, function-scoped stricter binary-search matching, multi-instance enumeration, and direct-sibling order.
- Removes the unsafe global `set_prolog_flag(unknown, fail)` directive responsible for the warning. No other existing AP2 predicate is removed.

## Windows acceptance commands (from extracted project folder)
```cmd
conda activate ons_ruleskg
swipl --version
semgrep --version
RUN_SELFTESTS.cmd
RUN_DEMO.cmd examples\search_binary.py
RUN_DEMO.cmd examples\search_linear.py
RUN_MULTI.cmd examples\sort_then_search.py
RUN_MULTI.cmd examples\sort_only.py
RUN_MULTI.cmd examples\no_swap_then_search.py
```

Required mixed-case output includes:
```
CANDIDATE: bubble_sort; function: find_number; AST region: ...
CANDIDATE: binary_search; function: find_number; AST region: ...
RELATION: bubble_sort BEFORE binary_search; function: find_number; regions: ...
```
Region IDs are exporter node IDs, not fabricated line numbers. Output should have **no** SWI-Prolog global `unknown` or `discontiguous` warnings. `sort_only` must contain no binary-search candidate. `no_swap_then_search` must not report bubble sort. No semantic correctness proof is claimed.

To replay the original actual Semgrep AST under multi mode:
```cmd
RUN_MULTI.cmd --ast-json tests\fixtures\semgrep_binary_ast.json
```
Expected one `binary_search` candidate.

For relational queries after `RUN_MULTI`:
```cmd
swipl -q -f none -s prolog\multi_classify.pl -s out\facts.pl -g "findall(A-R,algorithm_instance('find_number',A,R),M),writeln(M)" -t halt
```
Caution: `out/facts.pl` is overwritten on each demo, so run the mixed case immediately before querying if you want both.

## Current CI/build limitations
This sandbox has no `semgrep` or `swipl` binaries and cannot fetch them; Python-only tests can run. The extended test suite contains optional real Semgrep/Prolog tests that become active on office Windows. **No claim of successful mixed live recognition has been established until those tests run.** The synthetic contract trees in `tests/contract_ast.py` are not actual Semgrep outputs; they are clearly named contract tests to guard semantics in a local build with SWI-Prolog. The existing binary fixture is an actual Semgrep output.

## If mixed case returns UNKNOWN
- Save `out/ast.json` and `out/facts.pl`. Inspect the exact AST shapes for `For` at position 2, `If`/`Gt`, and `Container` tuple swap. Semgrep's debug serialization can change between versions.
- Correct the small Prolog navigation adapter for actual observed shape; **never rewrite the exporter to discard unrecognized AST nodes**.
- Keep `UNKNOWN` instead of claiming partial algorithm matches from loops alone.

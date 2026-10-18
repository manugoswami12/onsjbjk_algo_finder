# AP6 Requirements / Frozen Baseline Design

Date: 2026-10-09. Baseline: user-supplied `ap5.zip` (AP5, 37/37 Windows acceptance). This document is authoritative for the AP6 extension.

## Objective and non-objectives

**Objective:** detect two **interleaved logic threads** in one Python function using the *exact, unchanged* Semgrep OCaml AST JSON and Prolog tree facts. Demonstration: nested adjacent-swap bubble-sort operations interleaved with a polynomial rolling **hash-update** accumulator, fed from the same indexed array access in the same inner loop. Independently report each thread, its anchored AST region, and a *shared inner-loop* relationship. Preserve false-positive / false-negative test fixtures and report `UNKNOWN` when evidence is insufficient.

**Non-objectives:** no learning/Popper, ML, generalized patterns, automatic invariant synthesis, equivalence theorem, broad Python symbolic execution, clone matching, or language renaming. No modification to frozen ACE/CodeGraph or Semgrep AST representation.

## Non-negotiable invariants

1. Original AP2/AP3/AP5 `RUN_DEMO`, `RUN_MULTI`, `RUN_AP3_ACCEPTANCE`, `RUN_SELFTESTS`, public `candidate/1,2`, `algorithm_instance/3`, `main`, and `main_multi` remain unchanged in behavior.
2. All AST facts stay `ast_tag/2`, `ast_edge/3`, `ast_scalar/2`, `ast_node_count/1`. New AP6 Prolog predicates query them; no rewriting, feature loss or hand-edited AST export.
3. Require a **connected** logic thread: hash accumulator initialized before the outer loop, same accumulator on both sides of a polynomial recurrence in that inner loop, an input value indexed from one array, and the same accumulator returned *after* the outer loop. This is structural evidence of a rolling hash update, not proof of hashing suitability or collision resistance.
4. Detect bubble sort separately using existing AP5 exact comparison-and-swap predicate. Interleaving is reported **only** if the rolling-hash update lies in the same inner loop whose conditionally executed swap was matched, and both use the exact same array/index identities.
5. For different functions, arrays, indices, unrelated recurrence variables, swapped-out branch or absent recurrence, do not report interleaving. Avoid claims that `hash()`/`sorted()` necessarily reveal the library implementation algorithm.
6. The term `BEFORE` is retained only under AP5's strict direct-sibling relation; AP6 relation `INTERLEAVED_WITH` is a statement about one repeatedly traversed inner-loop body, not a whole-program runtime scheduling proof.
7. Keep existing tests and add independently named negative controls, synthetic contract tests and live Semgrep/SWI tests. Real-tool successes must not be fabricated when binaries are missing.

## Source example

`examples/interleaved_sort_hash.py` implements an array-adjacent bubble-sort loop with `digest = (digest * 31 + items[j]) % 1000000007` immediately preceding the conditional adjacent swap, with `digest = 0` before the loops and `return digest` after. This tracks a rolling digest of encountered compared elements. It is not a digest of the final sorted array and is not an independently verified cryptographic hash.

## Output (new opt-in `--threads` / `RUN_THREADS.cmd`)

- One line per `CANDIDATE: bubble_sort`, `CANDIDATE: rolling_hash_update` (not unsupported stronger name `hash_algorithm_implemented_correctly`), with concrete AST roots and bound evidence.
- One line `RELATION: rolling_hash_update INTERLEAVED_WITH bubble_sort` if **same** inner loop and matching array/index.
- No false `RELATION` where algorithms are in different functions / loops or the recurrence is unrelated.
- Existing AP5 outputs remain byte-for-byte compatible in their own modes.

## Acceptance gate

Run `RUN_AP6_ACCEPTANCE.cmd` on Windows with Semgrep + SWI-Prolog. Expect all pre-existing tests to pass, plus independent AP6 tests, and output with two candidates and an interleaved relationship on the positive real source. Negative cases must each suppress the inappropriate label/relation. If real AST encoding differs, inspect `out/ast.json`, fix the small Prolog navigation rule and add a regression; never modify the exact exporter to fit the matcher.

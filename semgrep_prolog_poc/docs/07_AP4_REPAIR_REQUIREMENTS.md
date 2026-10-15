# AP4 → AP5: surgical function-discovery repair

## Requirements, authoritative baseline and exclusions

Baseline: user-provided `ap4.zip` and Windows acceptance log, which reports 35 tests, 9 failures. Treat the complete Semgrep OCaml `AST_generic` JSON and the exact `ast_tag/2`, `ast_edge/3`, `ast_scalar/2` exporter as immutable contracts. Preserve AP1/AP2 legacy entrypoints, AP3 `--multi`, Windows/Linux runners, examples, tests, negatives, and multi-region output.

**R1** Find named function definitions in REAL Semgrep AST JSON, including the intermediate record payload underneath `FuncDef`. Do not use function names or Python `ast` to identify algorithms.

**R2** Localize each candidate to its actual function body, preserve variable unification and the existing bubble/binary patterns, enumerate all matches and print relative order only when justified by direct siblings.

**R3** Keep old AP2 rule path and all three AST predicates exactly unchanged. Fix no broader feature than required. Any reported candidate remains *structural*, never a proof of correct sorting or searching.

**R4** Add regression diagnostics for genuine Semgrep `DefStmt` encoding (not only synthetic `For` samples), negative cases and multiple algorithm instances. Avoid silent failure that merely reports `UNKNOWN: no named functions found` for a valid fixture.

**R5** Preserve commands `RUN_SELFTESTS.cmd`, `RUN_DEMO.cmd`, `RUN_MULTI.cmd`, `RUN_AP3_ACCEPTANCE.cmd` and analogous shell scripts. Run local available tests; distinguish skipped external tool tests from passed tests.

## Observed failure

Nine Windows tests fail because the new `function_definition/3` predicate requires `child(FuncDef, 'fbody', ...)`. The real Semgrep representation is `FuncDef -> value -> record -> fbody -> FBStmt -> value -> Block`. All subsequent `algorithm_instance_in/5` joins depend on `function_definition/3`, producing `UNKNOWN: no named functions found` even for the AP2 binary AST fixture.

## Correctness boundaries

- No reduction of raw AST, implicit transformation of conditional trees or extra AST facts.
- A structural match is not a guarantee of semantic equivalence. For example, a bubble-like nested compare-and-swap need not sort if loop coverage is wrong.
- Negative cases must not produce a false bubble-sort candidate; cross-function relationships must not be manufactured.
- Actual Windows Semgrep+SWI acceptance is required before declaring all failures resolved.

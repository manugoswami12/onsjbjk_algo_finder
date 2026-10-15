# AP9 requirements / architecture (2026-10-09)

## Scope and evidence contract
AP8 remains FROZEN. Preserve all AP8 Python, Prolog, CLI flags, examples and tests. AP9 adds an opt-in deterministic *reference-backed* structural matcher and a typed, reversible fact dialect. It does NOT claim to infer an algorithm name from unlabelled source, discover invariants, or decide semantic equivalence. Algorithm labels are user-supplied reference annotations, reported as **reference structural matches**, never mathematical correctness proofs.

## Requirements
R1. Preserve AP8 original `out/facts.pl` representation and its test expectations. Do not alter the pre-existing exporter, recognizers, or demo runner.
R2. A new lossless JSON-value exporter preserves string versus number versus boolean versus null, empty map versus array, map key and field order, exact numeric lexemes, and every nested node. Reject duplicate JSON object keys and nonstandard numeric constants rather than silently losing information. Original JSON whitespace/string-escape spellings are not part of *JSON value* losslessness.
R3. A deterministic Python reference compiler accepts a captured **Semgrep OCaml generic AST JSON**, user-annotated algorithm name, function name, and selected region (`body`, `for`, `while`, `if`, `assign`). It produces static Prolog terms representing the reference's AST. It must not use Python's `ast` module, ML, Popper, Semgrep match syntax, keyword labels or manually written per-algorithm predicates.
R4. A deterministic candidate compiler projects each scoped AST region in a target dump using the identical rules. Matching happens by generic SWI-Prolog unification of reference terms against ground candidate terms, with repeated local-variable binding consistency. External function names, operators, constants, control shape and statement order stay literal.
R5. Candidate matches are source-scoped and region-scoped. Expose matched function, AST-region address, and variable bindings; no mixing evidence across functions.
R6. Treat structural equivalence as an exact, narrow contract. Report `UNKNOWN` for unsupported structural variants. Avoid promising zero false positives/negatives for arbitrary semantics.
R7. Provide adversarial controls, changed builtin/operator/constant/reused-variable counterexamples and mutation/rename positives; machine-readable confusion-matrix evaluator with safe denominators, expected-result manifest, and no spurious claimed passes when swipl or semgrep unavailable.
R8. All new modules independently testable without affecting baseline; use Python standard library plus existing SWI-Prolog/Semgrep executables.

## Architecture
Semgrep OCaml AST JSON → (A) AP8 unchanged exporter, (B) opt-in typed fact export + reconstruction, (C) deterministic reference region projection + reference Prolog clauses → candidate region projection → Prolog unified matches + evidence → independent evaluation.

## Deliberate limitations
- Reference-pattern matching is **not generalization learning**. It is exact structural matching with locally scoped identifier-variable slots and nonsemantic Semgrep metadata removed from an *additional*, clearly separated projection.
- A label supplied by the reference author is not automatically validated. A match cannot prove the code truly sorts or hashes.
- Not all alpha-renamings are supported (comprehensions, reflection, dynamic binding, and nested scope resolution may require later frontends). Unknown rather than guessing.
- No complete CFG/SSA, reachability, or theorem proving. AP8's conservative audit remains available independently.

# AP8: Conservative structural audit (requirements and design)

## Baseline and purpose

Authoritative source: AP7 archive `onsjbjk_semgrep_prolog_AP7_direct_return_fix_20261009.zip`. The user reported 60/60 Windows tests passing for AP7. Preserve AP1–AP7 exact AST exporter, all existing Prolog predicates, runners and output formats; add an opt-in audit instead of changing established classifications.

**Objective:** reduce false-positive claims for bubble sort and the interleaved rolling-hash accumulator while preserving all previously recognized candidates. It is an AST structural audit, NOT program equivalence, reachability proof, invariant inference, Popper or a new parser.

## Requirements

R1. Keep exact Semgrep JSON and `ast_tag/2`, `ast_edge/3`, `ast_scalar/2` facts unmodified.

R2. For a stronger `bubble_sort` finding, independently verify outer `for i in range(len(a))` and inner `for j in range(len(a)-i-1)` bounds against the same array and loop variables used by adjacent compare-and-swap; allow renaming, not mistaken bounds, breaks, or continues.

R3. For a stronger `rolling_hash_update` finding, independently verify the original seed, recurrence and return PLUS: seed as a direct top-level assignment, recurrence as a direct statement of the inner loop body (not merely under `if False`), and return as a direct top-level statement. Do not borrow evidence from separate functions or arrays. Conservatively flag loops containing break/continue/return as unverified.

R4. Report `AUDITED_STRUCTURAL` only for the supported shapes. Report `UNVERIFIED` for legacy candidates whose additional checks cannot be established. Never print `ABSENT` or `INCORRECT` merely because matching fails.

R5. `INTERLEAVED_AUDITED` requires BOTH strong recognitions, same definition/outer/inner/array/index, with evidence. Keep legacy `--threads`, `--multi`, `--ast-json` unchanged.

R6. Regression tests: captured Semgrep AST *mutation* tests + live Semgrep Windows tests, negative controls for loop bounds, inaccessible branch, early exits, wrong-array links, and renamed names. Synthetic tests must be explicitly labeled synthetic, not proof of live AST compatibility.

R7. No third-party Python dependencies; Prolog only via existing SWI-Prolog. All API/runner changes additive.

## Scope and claims

This detects syntactic forms, not full Python behavior. `range`, `len`, identifiers and sequence operations may be dynamically rebound or overloaded; exceptions, aliasing, helper effects and conditional reachability require deeper analysis. A stricter syntactic match is NOT a sorting-correctness or hash-correctness proof. Unsupported variants may be `UNVERIFIED` rather than true negatives.

## Architecture

`source -> Semgrep OCaml AST_generic JSON -> AP7 exact facts -> AP7 candidates (unchanged) -> AP8 independently audited relationships -> AUDITED_STRUCTURAL / UNVERIFIED.`

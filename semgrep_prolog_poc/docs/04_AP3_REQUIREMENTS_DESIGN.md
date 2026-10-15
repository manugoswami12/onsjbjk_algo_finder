# AP3 requirements and frozen-interface design (2026-10-09)

## Goal and baseline
Preserve every AP2 source-to-OCaml Semgrep AST JSON fact; classify **two distinct algorithm regions within the same Python function**, using SWI-Prolog structural queries over the exact tree. The proof-of-concept case is an in-place adjacent-element bubble sort followed by iterative inclusive-bound binary search. Do not invoke Python's AST module, ML, Popper, Z3, clingo, or change the frozen CodeGraph/ACE/Wren pipeline. The uploaded `ap3.zip` is the baseline. Avoid deleting or renaming any existing public predicate or command. Preserve AP2's `candidate/1`, `candidate/2`, `main`, `RUN_DEMO`, `RUN_SELFTESTS`, fact schema, and replay.

## Distinct correctness claims
- Preserve complete Semgrep debug JSON as `out/ast.json`, and every JSON node, edge, tag, scalar in `out/facts.pl`. Existing exact fixture must retain 783 nodes, 1833 total emitted lines, including the original comments and the AST count. No new algorithm label in exporter.
- A **separate opt-in** `RUN_MULTI.cmd` mode enumerates algorithm instances for every named function; reports algorithm, region node ID, and evidence. Multiple hits are allowed; no `once` over all algorithms.
- `bubble_sort` requires **nested For loops, adjacent indexed comparison, and a reverse parallel assignment swap in the same conditional body**; do not accept just two loops or two array references.
- `binary_search` uses existing AP2 tested structural predicate requirements, bounded to one function/while region. Keep the old API and output intact. New multi-mode adds a directional-branch requirement to reduce false positives for typical two-branch code.
- Report a verified `before` relationship only if both recognized region roots are direct, ordered siblings in the SAME Semgrep `Block`; no invented chronology for nested/conditional regions.
- Missing evidence => `UNKNOWN`, not a claim of proof of absence. Each recognition is a *candidate*, not a semantic equivalence proof.
- CLI output is readable; warnings go away by removing hazardous `set_prolog_flag(unknown, fail)` from AP2. No `discontiguous` flood.
- Compatibility: AP2 command and tests must still run; new tests include one-function mixed, two-function split, negative cases, renamed variables, function-region ordering. Live tests must be run on a machine with both Semgrep and SWI-Prolog; synthetic fixtures are marked as synthetic, not represented as observed OCaml output.

## Fact interface (unchanged)
`ast_tag(N, Constructor)`, `ast_edge(Parent, Child, Key)`, `ast_scalar(N, Value)`, `ast_node_count(Count)`; numeric JSON list indices are quoted Prolog atoms, e.g., `'0'`. `Call -> Special -> Op('Plus')`; for-loops are `For` with header often `ForEach`; tuple literals/targets may be `Container(Tuple, ...)`, whereas single assignments are `Assign(LHS,token,RHS)`.

## High-risk logic table (critical: external I/O OR foundation used by >2 consumers)
| Component | Why critical | Failure modes | Safeguard/test |
|---|---|---|---|
| Semgrep CLI AST dump | external parser process | version changes, parse errors, partial stdout | existing error/timeout guards, live fixture contract |
| Flat fact serializer | Prolog boundary, basis for all inference | reordered fields, dropped nodes, quoting injection | exact AP2 fixture regression, stdlib exporter tests |
| OCaml structural navigation predicates | shared by binary, sorting, ordering | incorrect variants or list access | captured AST tests; explicit unknown on unsupported shapes |
| Region-to-function ownership | foundation for all matching | mixing algorithms between functions | multi-function isolation regression |
| Binary direction checks | algorithm-specific safety | reversed guard branches | negative mutation test; preserve legacy recognition separately |
| Parallel swap identification | algorithm-specific safety | comparison-only false positives, non-swaps | reversed-left/right pair constraints, missing swap negative |
| Prolog variable binding | foundation for every match | mistaken cross-variable or cross-array combination | renamed example, inconsistent index tests |
| CLI entrypoint and output paths | external SWI, filesystem | stale output, missing binaries, warnings | same AP2 runner + opt-in flag; preflight tests |
| Result enumeration and relationship calculation | basis for downstream querying | lost second result, spurious order | `setof` distinct regions and strict sibling-order query |

## Explicit limitation and release gate
As of code authoring, this build container does not provide `semgrep` or `swipl`; no claim of live Semgrep parse or SWI recognition unless run on user's office PC. Captured binary AST is real. Synthetic compound AST is a structural *contract test*, not an actual Semgrep dump. The release gate is live `RUN_MULTI.cmd examples\\sort_then_search.py`, then `RUN_SELFTESTS.cmd` (no skips), with `bubble_sort` and `binary_search` both observed and ordered. If actual Semgrep emits a materially different tuple or For representation, keep the exact AST and adapt only the generic navigation predicates after reviewing `out/ast.json`.

# AP5 repair handover (from uploaded ap4.zip)

## The exact defect and fix

The user's AP3 Windows run had **9 failed / 35 tests**, all through the common `UNKNOWN: no named functions found` path. `function_definition/3` in `prolog/ast_regions.pl` was wrongly attempting `child(FuncDef, 'fbody', FBStmt)`.

Actual Semgrep OCaml JSON (confirmed by `tests/fixtures/semgrep_binary_ast.json`) represents `DefStmt[1]` as a `FuncDef` constructor whose `value` edge points to a multi-field `record`, and **that record** owns `fbody`. The fix inserts `value(Kind, Fields), ast_tag(Fields, 'record')`, then looks up `child(Fields, 'fbody', FBStmt)`.

## Test evidence in this environment

- Captured real fixture contains `DefStmt → FuncDef(value) → record(fbody) → FBStmt(value) → Block`. Independent graph traversal reaches the body and enumerates the bubble-test synthetic nested `For` nodes plus the real `While` node.
- 37 tests in the enhanced suite; 20 passed, 17 skipped. External SWI-Prolog/Semgrep binaries are not installed here. **Do not claim successful end-to-end multi-algorithm recognition until the user's Windows acceptance rerun.**
- `tools/export_ast_facts.py`, `prolog/classify.pl`, `prolog/bubble_rules.pl`, and `prolog/multi_classify.pl` are unchanged from user-provided AP4 baseline. The exact AST schema and AP2 mode are preserved.

## Windows acceptance (Conda CMD, same folder as extracted package)

```cmd
RUN_AP3_ACCEPTANCE.cmd
RUN_MULTI.cmd examples\sort_then_search.py
RUN_MULTI.cmd examples\sort_only.py
RUN_MULTI.cmd examples\no_swap_then_search.py
RUN_DEMO.cmd examples\search_binary.py
```

Required outputs:

1. Full automated suite passes with 0 failures (now **37 tests**), including SWI/Live tests when those binaries are installed.
2. Mixed `find_number`: `CANDIDATE: bubble_sort`, `CANDIDATE: binary_search`, and `RELATION: bubble_sort BEFORE binary_search`.
3. Sort-only: bubble candidate but no binary candidate.
4. No-swap: binary candidate but not bubble candidate.
5. AP2 legacy `RUN_DEMO.cmd`: binary candidate as before.

## In case a later matcher still fails

The function-discovery bug masked any independent shortcomings in live OCaml tuple assignment representation. If `UNKNOWN: no named functions found` disappears but bubble detection still fails, save `out\ast.json`, `out\facts.pl` and the full first failing assertion. The real `For`, tuple assignment and `If` subtree must then be compared against the synthetic AP3 contract before touching algorithm rules. Never silently relax swap/comparison checks, which would raise false positives.

## Scope and limitations

This patch does NOT learn algorithms automatically, prove the correctness of sort/search, or guarantee Semgrep version-independent AST contracts. It repairs the shared AST navigation only and adds regression documentation/tests. Keep AP4 intact and extract AP5 to a separate directory.

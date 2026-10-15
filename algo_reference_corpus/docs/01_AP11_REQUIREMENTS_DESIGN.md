# AP11 Requirements and Design, 14 October 2026

## Objective
Ingest named functions from the pinned [`TheAlgorithms/Python`](https://github.com/TheAlgorithms/Python) Git checkout into the existing AP9 **generated Prolog reference_pattern/4** dialect, then ask the unchanged AP10 matcher to recognize matching structures in unknown Python. Extend the **knowledge** base rather than changing the successful AP10 recognizer.

## Protect the existing tool
AP10 (the sibling `semgrep_prolog_poc`) is a **read-only dependency**. All new code, SQLite data, `.pl` files, parsed AST temporary captures, evaluations, CMD wrappers and docs live under sibling `algo_reference_corpus`. Do not edit AP10 files, code, `out/ap10/catalog.json`, Prolog rules, or launch its runners with their default store during ingestion.

## Source quality and scope
TheAlgorithms/Python's categories `sorts`, `searches`, `hashes`, `strings` are currently real upstream categories; upstream is MIT licensed. The upstream file/function *names suggest identities* but are **not theorem-quality algorithm labels**. A source file may contain helpers, wrappers, test functions, nested functions and multiple reference variants. Every imported label remains `unreviewed` until explicit human approval. An unreviewed structural match is diagnostic only, never an algorithm proof.

Release 1 ingests at most 30 function signatures by default, evenly interleaving source files from categories. The shared SQLite schema includes `language`, but only `Python` has a tested parser/compiler backend. No automatic grammar translation for C, R, CLIPS or other languages is claimed.

## Data contract
Each immutable record carries `language`, source repository, full SHA Git commit, category, relative source path, function name and Semgrep AST path, region (`body`), ordinal, source/AST/pattern SHA256, structural fingerprint, clause path, status (`generated`, `skipped`, `error`), manual review status and reason. `refs/<label>.pl` is the standard AP9 Prolog reference clause. The SQLite DB is *metadata and search index*, not a new Prolog dialect. Generated patterns are inert data clauses read by the existing matcher. Upstream code is **never imported or executed**.

## Main flow
```text
pinned clean Git tree -> tracked safe .py files -> existing Semgrep capture
  -> existing AP9 functions() -> existing AP9 compile_reference()
  -> immutable AP9 .pl in AP11/refs + SQLite metadata
  -> user-reviewed labels -> disposable AP10 catalog
  -> existing AP10 scan() -> SWI-Prolog evidence or UNKNOWN
```

Semgrep subprocess has its current frozen 90-second timeout. Rejected path traversal/symlinks, parse failures and ambiguous function names must not generate approved patterns. `scan` defaults to **approved only** and searches a bounded list. No procedure is created to modify AP10 itself.

## Explicit non-goals
No inference of mathematical invariants, arbitrary rewrite equivalence, recursion-to-loop equivalence, cross-language normalized AST, dynamic source execution, function call semantics, alpha-equivalence beyond frozen AP9's contract, or zero false positives/negatives. The original AP10 block-subsequence behavior remains unchanged and may match structurally despite state-changing inserted statements.

## Acceptance
1. AP10's unchanged `RUN_AP10_ACCEPTANCE.cmd` passes on Windows before and after deployment; frozen default catalog identical.
2. AP11 offline tests pass; exact frozen compiler produces standard Prolog from captured genuine OCaml AST.
3. New local Git clone is pinned to recorded revision, corpus unmodified; `LICENSE.md` retained.
4. Pilot 20–30 functions across sorting/searching/hashing where supported, with every failure clearly recorded.
5. No errors or skipped entries may be queried as reference clauses; review action is explicit.
6. Multiple-reference Prolog load uses the **existing** validated AP10 bundler, not independent `-s` loads.
7. Hold out *new implementations*, plus negatives with changed operators/bounds, for evaluation. Count TP/FP/FN/TN and UNKNOWN separately. No acceptance claim until real SWI-Prolog run.

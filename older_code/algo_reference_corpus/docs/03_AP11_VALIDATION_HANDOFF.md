# AP11 Validation / Handoff | 14 October 2026

## Delivered state
**Additive Python ingestion utility built.** It has not been run against a live network-cloned `TheAlgorithms/Python` corpus in this sandbox. All code is in a separate `algo_reference_corpus` sibling of frozen `semgrep_prolog_poc`; no files from `ap12.7z` are included or overwritten.

## Actual evidence produced here
- Inspected frozen `ap12.7z`: existing `tools/reference_pattern.py` exposes `functions`, `path_string`, `compile_reference`, `compile_candidates`; `tools/ap10_cli.py` exposes `capture`, `scan`; `tools/ap10_reference_bundle.py` exposes `bundle_references`.
- Used original real captured Semgrep OCaml AST files `out/ap10/sort_signature.json` and `out/ap10/hash_signature.json` as offline reference inputs.
- Ran **11 / 11 offline tests passed**, Python compileall passed. Tests cover deterministic labels, symlinks/traversal rejection, fake Git origin rejection, altered worktree rejection, real AP9 compiler, original bundling of two reference clauses, SQLite metadata/approval, resumability, detected corrupted clauses, missing parser evidence and approved-only scan policy.
- Captured the original AP10 `catalog.json` and compiler SHA256 in tests before/after calls, with no changes.
- **Not performed here**: live Semgrep parsing of current upstream Git checkout, SWI-Prolog AP11 match run, Windows CMD execution, full AP10 regression on user computer, hold-out independent recognition benchmark.

## How to deploy
Unzip archive into `D:\ons_one_Drive_sync\ons_gemini\onsjbjk_pmi_gcd_cot\onsjbjk_wren_NT_1\onsjbjk_office_wren_NT_ace_utool_clingo` preserving subdirectories, beside `semgrep_prolog_poc`.

Use CMD, not PowerShell, after activating existing `ons_ruleskg` and adding `A:\swipl\bin` to PATH:

```cmd
cd /d "D:\ons_one_Drive_sync\ons_gemini\onsjbjk_pmi_gcd_cot\onsjbjk_wren_NT_1\onsjbjk_office_wren_NT_ace_utool_clingo\algo_reference_corpus"
where python
where semgrep
where swipl
call RUN_AP11_DOWNLOAD.cmd
call RUN_AP11.cmd revision
call RUN_AP11_ACCEPTANCE.cmd
call RUN_AP11.cmd status
```

`RUN_AP11_ACCEPTANCE.cmd` executes the **pre-existing AP10 acceptance runner** before and after ingestion, so that original runner may refresh its own legacy runtime outputs. AP11 ingestion and scanning operations do **not** touch the AP10 tree or default AP10 knowledge catalog.

## After a successful live pilot
Look in `store/references.sqlite3`, `store/refs/*.pl` and `store/ingest_summary.json`. `RUN_AP11.cmd status` lists up to 40 labels and identifies unreviewed records. Inspect original function source before approving a label. Use `RUN_AP11.cmd review LABEL approved`. Scan independent code with `RUN_AP11.cmd scan C:\path\to\new_code.py`. For first exploratory runs, `RUN_AP11.cmd scan C:\path\to\new_code.py --include-unreviewed` searches unreviewed references **as candidate matches only**.

For a larger sweep, `RUN_AP11.cmd ingest --limit 100` expands the first 30-function pilot; this is not a claim of universal recognition. References stay tied to their exact upstream Git commit and are not silently updated on subsequent cloning or fetching.

## Still to verify on Windows
| Check | Expected evidence | Status here |
|---|---|---|
| Frozen AP10 119 tests + 17 repeated subsection | `AP10 END-TO-END PASS` | Prior user Windows log passed; rerun required |
| Real clone / revision | exact 40/64-char HEAD and clean tree | Not run |
| 30 reference ingestion | generated/skipped/error counts and review statuses | Code + offline replay tested |
| End-to-end AP11 self-match | `AP11 LIVE INGEST->SCAN SMOKE PASS` | Not run; runner provided |
| Held-out unfamiliar source | true/false matches reported by identity | Not run, independent benchmark required |

## Important compatibility and boundaries
- AP11 uses the **current existing AP9 Prolog dialect**, not a newly invented format.
- Only local variables already captured by the frozen binder logic are generalized. Operators, constants, control-flow nesting and loop statement order retain the AP10 contract.
- Unreviewed names can be misleading. Filename labels are provisional evidence of source provenance only.
- AP11 default `scan` includes approved references only. Option `--include-unreviewed` reveals unreviewed matches, marked as structural candidates.
- Default scan selects at most 30 references, configurable to 100. Searches with `truncated=True` did **not** exhaust the database.
- Only Python is implemented. The SQLite `language` column supports separate future C/R/CLIPS ingestion backends.

## Exact files delivered
`RUN_AP11.cmd`, `RUN_AP11_DOWNLOAD.cmd`, `RUN_AP11_ACCEPTANCE.cmd`, `.gitignore`, `README.md`, `ap11/{__init__,source,bridge,database,ingest,recognize,cli,live_smoke}.py`, `tests/test_ap11.py`, and three `docs/` files. No flat files and no copies of frozen AP10.

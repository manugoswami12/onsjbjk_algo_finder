# AP12 full TheAlgorithms/Python ingestion and automatic fallback: Windows runbook

## Placement (changed/new files only)
Unzip the patch from the parent directory containing **`algo_reference_corpus`**, **`semgrep_prolog_poc`** and **`onsjbjk_algo_io_fallback_poc_v0_1`**. This patch adds files ONLY under `algo_reference_corpus`. It does not replace AP11 modules, the frozen Semgrep/Prolog project, the fallback proof of concept, or either database.

## Working CMD session

```cmd
conda activate ons_ruleskg
set "PATH=A:\swipl\bin;%PATH%"
cd /d "D:\ons_one_Drive_sync\ons_gemini\onsjbjk_pmi_gcd_cot\onsjbjk_wren_NT_1\onsjbjk_office_wren_NT_ace_utool_clingo\algo_reference_corpus"
where python
where git
where semgrep
where swipl
call RUN_AP12_SELFTEST.cmd
call RUN_AP12_FULL.cmd --max-files 5
call RUN_AP12_FULL.cmd
call RUN_AP12_VERIFY.cmd
call RUN_AP11.cmd status
```

The first limited run is a safe real-tool smoke test. The second command exhaustively visits every **Git-tracked `.py` file**, irrespective of category or function count. The command is **resumable**: run it again after an interruption. Do not run multiple ingestion CMD windows concurrently.

`RUN_AP12_FULL.cmd` returns exit code 2 when not all tracked sources are accounted for or when source/compiler/fallback errors are recorded. This does **not** mean the entire database was erased or rolled back: per-file successful results remain and are verified on restart. The JSON report identifies exceptional files for follow-up. Empty `__init__.py` files may be legitimately without functions but are still recorded as covered, not as generated algorithm signatures. Existing AP11 errors remain visible and immutable; no hidden retry/overwrite.

## Outputs

- `algo_reference_corpus/store/references.sqlite3`: **existing AP11 catalog**, all original rows/reviews kept; new `reference_pattern/4` clauses referenced here.
- `algo_reference_corpus/store/refs/*.pl`: new frozen AP9-style Prolog clauses only for supported functions, with source and pattern checksums.
- `algo_reference_corpus/store/ap12_fallback.sqlite3`: separate source coverage ledger and per-function observations, UNKNOWN and limitations included.
- `algo_reference_corpus/store/ap12_facts/*.pl`: deterministic, source-derived Prolog facts, one file per source, with SHA-256 verification.
- `algo_reference_corpus/store/ap12_full_report.json`: full manifest coverage, generated count, exact/fallback errors, omissions, unknowns.

Verify `tracked_sources == represented_sources`, `missing_sources == []`, `all_files_accounted == true`. **Do not equate this with 100% successful algorithm reference compilation.** Check `error_sources`, `ap11_skipped_sources`, and `ap11_files_with_error_rows` separately. Passing verification checks file integrity and coverage, NOT semantic equivalence.

## Automatically fallback after strict matching

```cmd
call RUN_AP12_SCAN.cmd "..\semgrep_prolog_poc\examples\candidate.py" --include-unreviewed
call RUN_AP12_SCAN.cmd "TheAlgorithms_Python\searches\binary_search.py" --category searches --include-unreviewed
```

`--include-unreviewed` makes this diagnostic only. Without it AP11 searches approved references only. The scanner runs frozen AP11/AP10 strict matching first. For any remaining functions, AP12 produces relationship evidence, invokes its separate Prolog router automatically, and optionally searches the inferred `sorts`/`searches` reference branches via the **same unchanged strict matcher**. Output labels: `AP10_THREAD` (strict structural candidate), `AP12_BRANCH` (broader routing candidate), `UNKNOWN` (insufficient evidence). They are not interchangeable.

AP11 currently enforces a `--limit 100` reference cap in each strict scan and orders references deterministically. A `truncated=True` report means matching is **not exhaustive across the whole reference catalog**, even if all 1,608 sources have been ingested. Do not declare universal recognition. No candidate receives automatic approval.

## What we validated locally and what still needs Windows
- 13 AP12 Python tests passed (real Git fixture, controlled mock capture and fallback, preservation of reviews, corruption detection, resume, per-function fallback, real-archive static search witness).
- 13 AP11 Python tests passed.
- The earlier 11/11 original fallback **live SWI-Prolog** tests were supplied by the user. The **new AP12 Prolog router and full Semgrep+SWI full-run** still require a live Windows check. The repo archive here lacks its local `.git` directory; full pinned ingestion cannot be truthfully claimed as already run.
- Local Python 3.13 dry analysis of the archived corpus: 1,608 Python files, 1,587 successfully parsed, 21 SyntaxError files, plus many files with UNKNOWN evidence. Some errors are invalid upstream syntax; compare on actual `ons_ruleskg` interpreter before making source-specific decisions.

## Protection
Never alter `semgrep_prolog_poc`, `onsjbjk_algo_io_fallback_poc_v0_1`, frozen rules or recorded AP11 evidence. Do not delete error rows to make reports look better. If the source revision changes, use a new pinned commit and keep earlier provenance.

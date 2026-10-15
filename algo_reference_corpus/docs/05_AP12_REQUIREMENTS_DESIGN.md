# AP12. Automatic fallback and exhaustive Git corpus ingestion
Date: 2026-10-14. Status: independent extension, not a modification of frozen AP9/AP10/AP11 or the standalone fallback.

## Goal
From the exact local, clean TheAlgorithms/Python Git checkout, visit every tracked `.py` file, use the existing Semgrep OCaml generic AST -> AP9 reference compiler -> AP11 immutable reference catalog; independently derive Python AST input/output dependency evidence -> standalone SWI-Prolog branch router; store those observations and their immutable generated `.pl` facts in a SEPARATE SQLite database; and offer a command that tries AP11 strict pattern scanning first, and automatically attempts the fallback for functions without a strict match.

## Invariants
- Never edit semgrep_prolog_poc, ap11 code, existing SQLite rows, or old fallback implementation.
- Never import/exec/eval any analysed upstream Python source. Treat AST/source as untrusted.
- No semantic proof / no auto-approval: fallback produces candidate branches, not algorithm labels. Keep `UNKNOWN` and unsupported features visible.
- AP11 remains an append-only structured reference store, all labels/hashes/clauses verified. Separate database for AP12 file ledger and input/output observations.
- Batch ingestion is resumable per file. Save one file at a time, display progress, allow bounded `--max-files N` tests, and verify all paths against `git ls-files -z` rather than directory globs. Root-level `.py` sources included.
- Strict row integrity: source content hash, pinned commit, and clause hash verified before reuse. Never claim complete until every tracked `.py` is accounted for. Distinguish coverage from successful template generation and confirmed algorithm recognition.
- Error and skip reasons are materialized. Windows paths and SQLite connections closed promptly.
- Fallback invocation is opt-in through `RUN_AP12_SCAN.cmd`, not hidden inside frozen AP11 commands.
- Preserve original `AP11.scan` approval gate. Unreviewed references are used only with explicit `--include-unreviewed`.
- Small resources, standard Python libraries, existing Semgrep and SWI-Prolog only.

## Data model
Existing `store/references.sqlite3` (AP11 unchanged), existing `store/refs/*.pl` (unchanged).
New `store/ap12_fallback.sqlite3`: file ledger keyed by `(git_commit,relative_path)` and per-function observations. New `store/ap12_facts/*.pl` immutable per-source Prolog fact files. JSON report `store/ap12_full_report.json` updated transactionally.

## Completion
`AP12_FULL_COVERAGE: PASS` only if every tracked Python source has a corresponding ledger row and every generated AP11 pattern and AP12 `.pl` file passes SHA-256 verification. Record separate counters for template errors/skips, fallback unsupported/errors, and eligible references. `AP12_FULL_COVERAGE` is not `ALL_ALGORITHMS_RECOGNIZED`.

## Critical logic (environment interface OR foundation for >2 downstream components)
| Logic | Critical because | Failure mode | Protection |
|---|---|---|---|
| Git revision and tracked inventory | Git interface; all downstream provenance | wrong repo/omitted files/modified source | verify root/origin/clean tree; `ls-files -z`; source_path guards; commit repeated on verification |
| Semgrep capture and AST parser | external process, source for labels and Prolog patterns | process fails/hangs/large AST | existing bounded capture, error row, per-file report, never run source |
| Frozen AP9 compiler + AP11 SQLite | frozen program interface and multiple consumers | overwritten patterns/review reset/bad hashes | reuse frozen API and AP11 immutable add/get; hash validation |
| Fallback extractor/Prolog | separate Python->SWI interface | overly broad false positive, process hang, warning swallowed | preserve exact POC predicates; strict stderr/timeout; UNKNOWN evidence |
| Idempotent file checkpoint | >2 downstream statuses/reports and Windows FS | crash leaves partial state, silently skipped retries | store ledger only after both sides committed; recompute when row missing; verify final completeness |
| Strict-first scan | AP11+SWI interface | automatic candidate mistaken for match | primary match labeled STRICT; fallback labeled CANDIDATE; approvals unchanged |
| Coverage verifier | reporting and audit foundation | full claimed with errors/omitted sources | compare against independent Git tracked manifest; inspect every persisted hash |

## Non-goals
No universal semantic equivalence checker; no static inter-procedural proof; no recategorization based on filename; no feature deletion, no normalization loosening, no Popper/ML.

## Limitations of extended fallback
AP12 has a dedicated extra observation for bisect-style binary-search variants; it leaves recursive/stdlib wrappers and unsupported control flow as UNKNOWN. The AP12 Prolog router is intentionally separate from the tested v0.1 router. Top-level functions are the current fallback scope, even though Semgrep/AP11 may discover nested/class methods as exact reference candidates. No exact semantic claim is promoted by fallback routing. The 100-reference AP11 strict scan limit remains in force; automatic routing selects candidate categories but does not provide exhaustive recognition.

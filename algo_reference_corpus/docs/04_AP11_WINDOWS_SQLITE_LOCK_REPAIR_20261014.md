# AP11 Windows SQLite file-handle repair | 14 October 2026

## Observed defect

In `session_14-10-26_a.txt`, the AP10 protected baseline passes (119 tests and separate 17 AP10 tests). AP11 offline tests fail on Windows with `PermissionError: [WinError 32]` while `tempfile.TemporaryDirectory` attempts to remove `store/references.sqlite3`. Five test errors show the same file-lock symptom.

## Root cause

AP11 used `with connect(store) as db:` throughout. The original `connect()` returned a raw `sqlite3.Connection`. Python's `sqlite3.Connection.__exit__` commits or rolls back a transaction but **does not close the connection**. SQLite file handles thus remained live until garbage collection; Windows refuses removal of the open database. POSIX can unlink open files, hiding the bug in earlier Linux checks. Git's CRLF messages are warnings, not this failure.

## Design and Python pseudocode

```python
@contextmanager
def connect(store):
    db = sqlite3.connect(store / 'references.sqlite3')
    try:
        configure_rows_and_schema(db)
        with db:             # preserve existing transaction semantics
            yield db         # caller continues using `with connect(store) as db`
    finally:
        db.close()           # deterministic release, even when exceptions occur
```

## Activity / critical-logic review

| Activity | Module | Critical? | Test / safeguard |
|---|---|---|---|
| Database file open / close | `ap11/database.py` | Yes: external OS resource, used by all AP11 callers | Assert post-context queries raise `ProgrammingError` |
| Transaction commit / rollback | `ap11/database.py` | Yes: data correctness & persistence | Exception rollback regression |
| Ingestion, review, scan, CLI | Unchanged AP11 modules | Depend on shared database connection | Existing 11 tests and Windows acceptance |
| Git, Semgrep, SWI-Prolog, AP10 | No changes | Frozen/external | AP10 baseline before and after |

**Surgical change:** Only `ap11/database.py` and `tests/test_ap11.py` are code changes. `connect()` is intentionally a context manager now: using it **without** a `with` block is unsupported. Every supplied AP11 caller already uses the documented `with` syntax. Nested `with db:` in `add()` and `approve()` continue to commit transactions normally.

## Installation and verification

Extract the small repair ZIP into the *parent* directory containing `algo_reference_corpus` and `semgrep_prolog_poc`, preserving directory paths. Overwrite only the named AP11 files. Do **not** overwrite the `store` directory or the `TheAlgorithms_Python` clone; do not edit frozen AP10.

From existing activated `ons_ruleskg` Windows CMD:

```cmd
cd /d "D:\ons_one_Drive_sync\ons_gemini\onsjbjk_pmi_gcd_cot\onsjbjk_wren_NT_1\onsjbjk_office_wren_NT_ace_utool_clingo\algo_reference_corpus"
python -m unittest discover -s tests -v
call RUN_AP11_ACCEPTANCE.cmd
call RUN_AP11.cmd status
```

The new suite contains 13 cases (11 original + 2 lifecycle regressions). `RUN_AP11_ACCEPTANCE.cmd` will execute the protected AP10 baseline again, perform live ingestion and scan, then recheck AP10. **Offline tests here are not Windows acceptance.** Expected final success line is `AP11 LIVE ACCEPTANCE PASS`; examine any new traceback instead of assuming success.

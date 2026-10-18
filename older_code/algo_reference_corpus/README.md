# AP11: additive algorithm reference ingestion (14 October 2026)

**Do not merge into or overwrite `semgrep_prolog_poc`.** Extract this entire folder beside it:

```text
onsjbjk_office_wren_NT_ace_utool_clingo/
  semgrep_prolog_poc/           FROZEN AP10, untouched
  algo_reference_corpus/       NEW AP11 folder (this package)
    RUN_AP11_DOWNLOAD.cmd
    RUN_AP11.cmd
    ap11/                     Python modules
    docs/                     Design + pseudocode + acceptance
    tests/                    Offline tests
    TheAlgorithms_Python/     populated by Git; not supplied
    store/                    populated by AP11; not supplied
```

Use Windows CMD with your already-working `ons_ruleskg` environment and portable SWI-Prolog:

```cmd
set "PATH=D:\ons_miniconda;D:\ons_miniconda\Scripts;%PATH%"
conda activate ons_ruleskg
set "PATH=A:\swipl\bin;%PATH%"
cd /d "D:\ons_one_Drive_sync\ons_gemini\onsjbjk_pmi_gcd_cot\onsjbjk_wren_NT_1\onsjbjk_office_wren_NT_ace_utool_clingo"
cd semgrep_prolog_poc
call RUN_AP10_ACCEPTANCE.cmd
cd ..\algo_reference_corpus
where semgrep
where swipl
call RUN_AP11_DOWNLOAD.cmd
call RUN_AP11.cmd revision
python -m unittest discover -s tests -v
call RUN_AP11_ACCEPTANCE.cmd
call RUN_AP11.cmd status
```

Read the candidate labels listed by `status`, inspect source functions and then approve a correct reference label:

```cmd
call RUN_AP11.cmd review py_your_generated_label approved
call RUN_AP11.cmd scan "C:\path\to\unfamiliar.py"
```

For research only, use `scan "C:\path\to\unfamiliar.py" --include-unreviewed` without approval. Such matches are provisional. In a scan, `--limit` applies to **number of reference patterns** (default 30, max 100), not number of matches. `truncated=True` means coverage was intentionally partial. `--category sorts` narrows the search; `--label py_...` tests one reference. Use `ingest --limit 100` after the 30-function pilot has been independently reviewed. The SQLite DB resumes already-present references without replacing them. Check `store/ingest_summary.json` and `store/references.sqlite3`.

The importer is **not a new parser or recognizer**. It calls the unchanged `semgrep show dump-ast --json`, frozen `compile_reference()`, and AP10's bundled Prolog scan. The generated `.pl` clauses retain AP9's AST-bound variable roles, literal/operator constraints and statement nesting. Recognition is structural and has no guarantee of mathematical equivalence.

No Python examples are imported, executed, or run as tests. The upstream license `TheAlgorithms_Python/LICENSE.md` stays with the checkout. It is an MIT-licensed educational repository, not a correctness oracle. Repository: https://github.com/TheAlgorithms/Python

**Validation scope:** This build includes automated tests against the exact AP9 library supplied in `ap12.7z`, plus offline Semgrep fixture replay. Actual live Windows Semgrep, SWI-Prolog, GitHub network clone, and AP10 regression must be run on the office computer. AP11 ingestion and scanning never write under `semgrep_prolog_poc`; the original AP10 acceptance runner, when called by the AP11 acceptance script, can refresh its own existing runtime outputs as usual. `RUN_AP11_ACCEPTANCE.cmd` also runs an actual Semgrep-to-SWI-Prolog self-match of the first imported reference. That proves interoperability, **not held-out generalization**.

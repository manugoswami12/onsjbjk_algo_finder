# Completely separate input/output fallback POC (v0.1)

Extract the zip beside `algo_reference_corpus` and `semgrep_prolog_poc`.
It does not modify, call, or import any frozen project code or database.

**Windows CMD (existing conda and SWI-Prolog):**

```cmd
conda activate ons_ruleskg
set "PATH=A:\swipl\bin;%PATH%"
cd /d "D:\ons_one_Drive_sync\ons_gemini\onsjbjk_pmi_gcd_cot\onsjbjk_wren_NT_1\onsjbjk_office_wren_NT_ace_utool_clingo\onsjbjk_algo_io_fallback_poc_v0_1"
call RUN_FALLBACK_POC.cmd
call RUN_FALLBACK_POC.cmd examples\mixed.py
call RUN_FALLBACK_POC.cmd ..\semgrep_prolog_poc\examples\candidate.py
```

The first command executes 11 real SWI-Prolog routing checks. Failure is fatal.
Use `call RUN_STATIC_SELFTEST.cmd` to test the Python evidence extractor even if
Prolog is absent. For extra checks:

```cmd
python -m unittest discover -s tests -v
python run_poc.py examples\reverse.py --json
```

**Outputs:** evidence with line numbers, may-depend-on input information,
`sequence_rearrangement`, `comparison_driven_reordering`, `indexed_lookup`,
`interval_lookup`, or `unknown`. These are candidate **branch** names, not
claims that the program correctly implements bubble sort or binary search.

No new packages, internet, Git clone, ML, SQLite, or external datasets needed.
Unknown input Python source is **never executed**. The POC is intentionally
limited; read `docs/01_REQUIREMENTS_DESIGN.md` before evaluating results.

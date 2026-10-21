# AP13 polyglot_logic — handover (16 Oct 2026)

Branch `claude/wizardly-darwin-lb95nf`. All numbers are measured on the frozen Rosetta held-out set (789 files, 8 languages); details are in the docs.

| Layer | Files | Status |
|---|---|---|
| v1–v2.1 exact matcher: tree-sitter / SWI → facts → canon/slice → Prolog leaf match, plus learn-dir, validate, generalize | `tools/cli.py lower_*.py fact_io.py knowledge_store.py report.py`, `prolog/canon.pl slice.pl leaf.pl evidence.pl main.pl lower_prolog.pl`; docs 01–07 | **done**: precision 97.2% (35/36), recall 6.4%, 0 wrong on negatives |
| v3/v3.1 family branching + one explained outcome per file | `prolog/roles.pl families.pl family_main.pl`, `tools/family_scan.py family_eval.py family_cases.py outcome.py library_families.py`; docs 08–09 | **done**: test half precision 85.9%, recall 18.3%, coverage 67.1% |
| v4 Prolog normal form: every program → executable Prolog, logic trace, I/O fallback | `tools/to_prolog.py lisp_to_prolog.py io_trace.py io_catalog.py io_eval.py`, `prolog/interp.pl run_main.pl native_main.pl`; doc 10 | **prototype**: Python/C/Java/Rust/R/Lisp translated and run; Prolog run natively; 824 corpus functions run; last dev run 76% precision, 8% recall (before the last fixes) |

## Run
```
SETUP_AP13.cmd                              (Windows; SETUP_AP13.sh on Linux): pip deps, grammars, corpus, Rosetta
python -m unittest discover -s tests        56 tests
RUN_AP13.cmd learn-dir store\TheAlgorithms_Python ; validate ; scan <file>
python tools\outcome.py --rosetta store\rosetta --store store --split test
python tools\io_catalog.py learn store\TheAlgorithms_Python store\catalog.json
python tools\io_eval.py --rosetta store\rosetta --catalog store\catalog.json --split dev
```

## Open work (v4)
1. **Lisp in-place sorts returning NIL.** When the function wrote to an input list, take the final list as its output. The change was prepared and not applied: `run_main.pl` should print the write count, and `io_trace.split_ok` / `effective` should use it.
2. **Haskell translator** to the normal form (equations, `where`, `map`/`foldr`/`iterate`/`zipWith`).
3. **Missing interpreter builtins** (`lambda`, dicts, Java `new int[n]`, `charAt`/`subList`, Rust ranges and macros), plus a battery for more signatures.
4. **Grade SAME_FUNCTION by behaviour:** correct when the task's truth reference gives equal outputs.
5. **Combiner:** use the v3.1 outcome first and v4 for its UNKNOWNs, then measure the test half once.

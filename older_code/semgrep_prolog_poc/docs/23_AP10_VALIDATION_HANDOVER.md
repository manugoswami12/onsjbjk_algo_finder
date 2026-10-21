# AP10 Validation and Handover

## Files to add, no existing files replaced
```
semgrep_prolog_poc/
  RUN_AP10.cmd
  RUN_AP10_ACCEPTANCE.cmd
  tools/ap10_cli.py
  prolog/ap10_threads.pl
  tests/test_ap10_composition.py
  tests/fixtures/ap10/{sort_reference,hash_reference,interleaved_with_extra,separate_functions}.json
  examples/{ap10_sort_reference,ap10_hash_reference,ap10_mixed}.py
  docs/{21_AP10_REQUIREMENTS_DESIGN,22_AP10_PSEUDOCODE_ACTIVITY_CRITICAL,23_AP10_VALIDATION_HANDOVER}.md
```

## Windows CMD
Run from `semgrep_prolog_poc` (the already validated AP9 project root):
```
conda activate ons_ruleskg
set "PATH=A:\swipl\bin;%PATH%"
RUN_AP10_ACCEPTANCE.cmd
```

Then learn two separate algorithm references and scan a mixed implementation:
```
RUN_AP10.cmd learn sort_signature examples\ap10_sort_reference.py sort_reference
RUN_AP10.cmd learn hash_signature examples\ap10_hash_reference.py hash_reference
RUN_AP10.cmd scan examples\ap10_mixed.py
```

Expected logical result, pending real Windows execution:
```
AP10_THREAD: sort_signature; ...
AP10_THREAD: hash_signature; ...
AP10_RELATION: ... relation: shared_loop; witness: ...
```

To add a new reference from your own code without changing logic:
```
RUN_AP10.cmd learn my_reference path\to\implementation.py exact_function_name
RUN_AP10.cmd scan path\to\unknown_program.py
```

Existing labels are immutable. If you want a new reference implementation,
give it a new label (e.g. `sort_variant_two`) rather than changing old rules.
Catalog: `out\ap10\catalog.json`; generated `.pl` references remain under
`out\ap10`. This is not a binary knowledge graph or a new database.

## Validation performed here
- Disposable pre-code feasibility test: sorting and hashing independently
  matched both original and renamed mixed captured ASTs. Incorrect state
  rejected hash while retaining sort, and incorrect bounds rejected both.
- Offline regression tests: AP9 suite + 14 AP10 tests run, zero failures;
  6 new SWI tests skipped because SWI not installed here.
- Source preservation: compare every user-supplied AP9 file's SHA-256 with
  the patched tree. Patch only contains **new** files, no existing files.

## Acceptance condition
- Run the Windows CMD gate; it runs the pre-existing AP9 acceptance script,
  AP10 tests, and live Semgrep/SWI execution against fresh Python examples.
- The CMD gate requires evidence of two AP10_THREAD lines and a shared_loop.
- If a gate fails, AP9 remains frozen and usable. Do not promote AP10.

## Non-claims
`AP10_THREAD` means necessary reference syntax and variable relations were
found in this candidate. It does not prove correctness, reachability or any
mathematical invariant. `shared_loop` means matched AST loop identities overlap,
not that the two logical threads always execute together. No ML, Popper or
semantic learning has been introduced.

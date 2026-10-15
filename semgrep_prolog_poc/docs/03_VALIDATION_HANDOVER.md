# AP2 Validation and handover (9 October 2026)

## Proven from this build environment

- The user-supplied `ap1.zip` included a **real 783-node Semgrep OCaml AST** at `out/ast.json`.
- The original 1,831 logical Prolog facts were compared with newly generated facts **as multisets**: equality PASS. Only predicate grouping, comments, and fact order changed.
- Operator representation confirmed from real fixture: values `FloorDiv`, `Plus`, `Minus`, `LtE`, `Eq`, `Lt` occur beneath the `Op` constructor, *not* as constructor tags.
- Python standard-library unit tests, AST structure checks, and runner preflights are executed on this build machine.
- The Prolog file now includes node-by-node AST navigators and a variable-consistent binary-search candidate rule.

## Not yet independently proven on this build machine

This environment has no `semgrep` binary and no `swipl` binary. **Live Prolog evaluation is not claimed to have passed here.** The tests that actually call SWI-Prolog and Semgrep are included and will execute automatically on a Windows machine with both commands on PATH. An unexpected AST-version difference or Prolog bug must be treated as a failed acceptance gate and fixed, rather than declaring this project complete.

## Final user acceptance sequence (Windows CMD in project directory)

```cmd
where semgrep
where swipl
RUN_SELFTESTS.cmd
RUN_DEMO.cmd --ast-json tests\fixtures\semgrep_binary_ast.json
RUN_DEMO.cmd examples\search_binary.py
RUN_DEMO.cmd examples\search_linear.py
```

Expected outcome: all tests PASS with **no skips**, captured AST and binary example report `CANDIDATE: binary_search`, and linear example reports `UNKNOWN`. Warnings about `discontiguous` predicates should be absent. If `swipl` is not found, locate the installed portable executable and add its `bin` directory to PATH in this CMD session.

The real tests cover: actual captured 783-node positive, changed operator negative, changed while-bound negative, changed midpoint-name negative, variable rename positive, and live Semgrep binary/linear examples.

## Files changed / preserved

| File | Disposition |
|---|---|
| `tools/export_ast_facts.py` | Surgical change: group facts by predicate; preserve original `atom`, `flatten`, CLI and generic facts |
| `prolog/classify.pl` | Replace incorrect tag lookup with real AST_generic `Op`-scalar navigation, add unification and scope-aware rule; retain `candidate/1`, `main/0` |
| `tools/run_demo.py` | Keep old invocation, add optional `--ast-json` replay; preserve output and fail nonzero on tool errors |
| `RUN_DEMO.cmd`, `RUN_DEMO.sh` | Unchanged |
| `examples/search_binary.py`, `examples/search_linear.py` | Unchanged |
| `tests/test_exporter.py` | Unchanged original tests |
| `tests/test_real_ast_contract.py` | New structural/real-dump/SWI/negative-control tests |
| `tests/test_runner_preflight.py` | New external-entrypoint preflight tests |
| `tests/fixtures/semgrep_binary_ast.json` | New copy of user's real OCaml AST dump (not manufactured) |
| `RUN_SELFTESTS.cmd`, `RUN_SELFTESTS.sh` | New convenient test runners |
| `docs/*`, `README.md` | Design, pseudocode, critical logic, validation and runbook |
| `out/*` | Sample AST preserved and generated facts refreshed from it |

Do not integrate with frozen CodeGraph or ACE until the real Windows acceptance sequence passes.

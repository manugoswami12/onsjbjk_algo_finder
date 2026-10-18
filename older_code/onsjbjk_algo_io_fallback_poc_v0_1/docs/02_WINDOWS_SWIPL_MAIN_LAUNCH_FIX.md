# AP12 input-output fallback POC, Windows SWI-Prolog startup repair

## Requirement
Preserve every frozen AP9/AP10/AP11/SQLite/reference file. Repair only the
independent `onsjbjk_algo_io_fallback_poc_v0_1` runner that times out in Windows.

## Root cause
The earlier Python subprocess invoked `swipl -q -s prolog/route.pl -- facts.pl`.
`-s` **loads** the Prolog file; it does not call its `main/0` predicate.
An interactive SWI-Prolog session can therefore wait for console input until
Python's 25-second limit expires. The route predicates were not being reached.

## Surgical pseudocode
1. Derive facts from Python AST without importing or executing unknown source.
2. Save facts in an independent temporary file.
3. Start `swipl -q -s route.pl -g main -t halt -- facts.pl`.
4. Pass `stdin=DEVNULL` so execution never blocks on interactive input.
5. Check exit code, stderr and a `ROUTE` line for each analyzed function.
6. Return routes, otherwise report an explicit error.

## Activity classification
- Fact generation: unchanged (`facts_from` in `run_poc.py`).
- Process execution: changed (`route_live` in `run_poc.py`).
- Output validation: one extra no-output guard (`route_live`).
- Regression tests: new `tests/test_prolog_entrypoint.py`.
- Prolog routing rules: unchanged (`prolog/route.pl`).

## Verification
The Python mocked launch-contract tests verify `-g main`, `-t halt`, `--`,
noninteractive stdin, timeout handling and rejection of missing output. These
tests cannot substitute for live SWI-Prolog on the user's Windows computer.

Run from the prototype root in `ons_ruleskg`, after adding SWI-Prolog to PATH:

```
python -m unittest discover -s tests -v
call RUN_FALLBACK_POC.cmd
call RUN_FALLBACK_POC.cmd examples\mixed.py
```

A correct first run ends with `POC SWI-PROLOG LIVE ACCEPTANCE: 11/11 PASS`.
An unexplained Prolog timeout after this repair is a new issue and should be
investigated using its fresh output rather than extending the timeout blindly.

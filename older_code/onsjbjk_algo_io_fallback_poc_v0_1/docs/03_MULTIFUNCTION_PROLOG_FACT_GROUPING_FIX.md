# Separate input/output fallback POC: multi-function SWI-Prolog fact grouping fix

## Reported Windows failure

`RUN_FALLBACK_POC.cmd ..\algo_reference_corpus\TheAlgorithms_Python\searches\binary_search.py`
failed with SWI-Prolog warnings saying `Clauses of program/2 are not together` and
`Clauses of observed/3 are not together`.

The earlier single-function `..\semgrep_prolog_poc\examples\candidate.py` worked and
routed to `indexed_lookup, interval_lookup`.

## Requirement / design

- Fix only the independent proof-of-concept fact serialization, not frozen AP9,
  AP10, AP11, the TheAlgorithms checkout, or the actual Prolog router.
- Preserve identical facts, function IDs (`f1`, `f2`, ...), evidence lines,
  anonymous labels, Prolog predicates, and route semantics.
- Keep strict failure on any Prolog warnings or errors; **do not suppress them**.
- Candidate source is parsed statically and never executed.

## Root cause

`run_poc.py:facts_from` originally serialized facts by function:

```prolog
program(f1, anonymous).
observed(f1, returned_input, 2).
program(f2, anonymous).
observed(f2, returned_input, 5).
```

When SWI-Prolog consulted this file it emitted discontiguous predicate warnings.
The runner intentionally treats stderr as an error, so the real multi-function
module could not be analysed.

## Pseudocode / activity classification

**Fact output:**

```python
lines = [comment]
for each analysis in original order:
    output program(f_i, anonymous)
for each analysis in original order:
    for each evidence kind in sorted order:
        for each evidence line in sorted order:
            output observed(f_i, kind, line)
return text with final newline
```

**Validation:**

- `program/2` clauses occur in a single contiguous block.
- `observed/3` clauses occur in a single contiguous block.
- Every function receives a program fact, including zero-evidence functions.
- Fact names remain internal fixed identifiers (no source-text injection).
- Mocked Prolog launch confirms all function IDs are preserved.
- Existing Windows live SWI acceptance remains unchanged.

**Critical interface:** the Prolog fact writer must preserve predicate grouping
and the exact clause syntax; Prolog routing consumes these facts unmodified.

## Changed files (surgical ZIP)

- `onsjbjk_algo_io_fallback_poc_v0_1/run_poc.py`: group all `program/2` clauses
  before all `observed/3` clauses. No recognition criteria changed.
- `onsjbjk_algo_io_fallback_poc_v0_1/tests/test_prolog_entrypoint.py`: add
  regression cases covering multiple functions and a function without evidence.
- This note, `docs/03_MULTIFUNCTION_PROLOG_FACT_GROUPING_FIX.md`.

## Windows installation

Extract the patch ZIP into the **parent directory containing**
`onsjbjk_algo_io_fallback_poc_v0_1`, preserving paths and replacing existing
files. Do not extract the nested directory into itself.

From the existing `(ons_ruleskg)` CMD in the fallback POC directory:

```cmd
call RUN_FALLBACK_POC.cmd
python -m unittest discover -s tests -v
call RUN_FALLBACK_POC.cmd ..\semgrep_prolog_poc\examples\candidate.py
call RUN_FALLBACK_POC.cmd ..\algo_reference_corpus\TheAlgorithms_Python\searches\binary_search.py
```

The first command should still finish with `11/11 PASS`.
The last command should **complete without discontiguous-clause warnings** and
print one report per supported top-level function. It may legitimately report
`unknown` for some/all functions; routing does not prove semantic identity.

## Test evidence

- 18/18 local Python tests passed (includes 3 new multi-function tests).
- 11/11 static evidence self-tests passed.
- SWI-Prolog itself is not installed in the test container. The user's Windows
  environment is the definitive live integration check for this patch.

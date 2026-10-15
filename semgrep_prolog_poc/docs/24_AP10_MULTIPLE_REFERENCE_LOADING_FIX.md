# AP10: multiple-reference SWI-Prolog loading repair

## Observed Windows failure

The baseline AP9 suite passed but six AP10 live tests failed on the same
SWI-Prolog warning: `Redefined static procedure reference_pattern/4`.
AP10 loaded independently generated `sort.pl` and `hash.pl` as separate
sources with the same predicate indicator; later loads can overwrite clauses.

## Design and activity classification

| Activity | Program | Critical? | Safeguard |
|---|---|---|---|
| Read, validate, aggregate AP9 reference clauses | `tools/ap10_reference_bundle.py` | YES: Prolog boundary, shared by tests + CLI | one clause per reference, label check, no injected directives |
| Learn/run CLI | `tools/ap10_cli.py` | YES: external SWI interface | atomically build a combined read-only view |
| Prolog thread recognition | `prolog/ap10_threads.pl` **UNCHANGED** | YES: base for all matches | no logic changes |
| Live and adversarial tests | `tests/test_ap10_composition.py` | YES: external interface | load combined source as production code does |

## Deterministic pseudocode

```python
catalog = read_catalog()
reference_clauses = []
for entry in catalog:
    clause = read_original_ap9_reference(entry)
    validate_one_clause_correct_label_no_directives(clause)
    reference_clauses.append(clause)
atomic_write('all_references.pl', reference_clauses)
run_swipl('reference_match.pl', 'ap10_threads.pl',
          'all_references.pl', 'target.pl')
```

All original AP9-generated per-algorithm files remain untouched. No Prolog
warning suppression, `multifile` changes, learning changes, or new runtime
libraries are needed. The one-file view is regenerated deterministically.

## Windows verification

```cmd
conda activate ons_ruleskg
set "PATH=A:\swipl\bin;%PATH%"
RUN_AP10_ACCEPTANCE.cmd
RUN_AP10.cmd learn sort_signature examples\ap10_sort_reference.py sort_reference
RUN_AP10.cmd learn hash_signature examples\ap10_hash_reference.py hash_reference
RUN_AP10.cmd scan examples\ap10_mixed.py
```

Run `learn` only for labels not already in the catalog. Acceptance remains
pending real SWI-Prolog execution on Windows, despite passing offline tests.

# AP8 pseudocode, activity grouping and critical logic

## Detailed Python-style pseudocode (design only, not new Python parser)

```python
for definition in prolog_function_definitions(ast_facts):
    raw_candidates = enumerate_all_legacy_candidates(definition)
    for candidate in raw_candidates:
        if candidate.algorithm == 'bubble_sort':
            outer, inner = trace_nested_for(candidate.region)
            outer_var, outer_iterable = for_each_structure(outer)
            inner_var, inner_iterable = for_each_structure(inner)
            if (outer_iterable == range(len(candidate.array))
                and inner_iterable == range(len(candidate.array) - outer_var - 1)
                and inner_var == candidate.swap_index
                and not any_break_continue_return(outer)):
                yield audited(candidate, evidence='canonical bounded nested loop')
            else:
                yield unverified(candidate, 'bounds/flow not established')
        elif candidate.algorithm == 'rolling_hash_update':
            seed, outer, inner, update, return_ = retrieve_matched_nodes(candidate)
            if (direct_top_level_assignment(seed)
                and direct_statement_of_inner_loop(update, inner)
                and direct_top_level_return(return_)
                and not any_break_continue_return(outer)):
                yield audited(candidate, evidence='direct unconditional update')
            else:
                yield unverified(candidate, 'thread flow not established')
        else:
            yield unverified(candidate, 'no AP8 audit for this algorithm')

    for sorting, hashing in all_pairs_of_audited_candidates(definition):
        if (sorting.outer == hashing.outer
            and sorting.inner == hashing.inner
            and sorting.array == hashing.array
            and sorting.index == hashing.index):
            emit('INTERLEAVED_AUDITED', sorting.region, hashing.region)
```

## Activity types and distinct modules

| Activity | Module | Purpose |
|---|---|---|
| External AST and fact conversion | Existing `run_demo.py`, `export_ast_facts.py` | Preserve exact data; unchanged logic |
| Generic AST navigation / syntactic loop validation | `prolog/audit_ast.pl` | Reusable `range`, `len`, loop-variable, direct-statement helpers |
| Algorithm-specific conservative checks | `prolog/audit_rules.pl` | Bubble bounds and hash direct-update evidence |
| Output/query | `prolog/audit_classify.pl` | Audit statuses, regions, relation, never assert false absence |
| CLI selection | `tools/run_demo.py`, `RUN_AUDIT.cmd` | Opt-in audit; all prior modes retained |
| Verification | `tests/test_audit_recognition.py` | Real-capture mutations and Windows live tests |

## Critical logic assessment

Per user definition, critical means (1) boundary with external environment/program, or (2) used as base by >2 consumers.

| Component | Critical reason | Failure mode | Guard/test |
|---|---|---|---|
| `run_demo.py` | External Semgrep + SWI-Prolog subprocess interface | Wrong executable/goal, stale output | Preserve existing paths, add exclusive `--audit`, smoke test |
| `export_ast_facts.py` | External JSON → Prolog schema; all recognition depends on it | AST data lost or changed | Byte-identical preservation, legacy tests |
| `child/3`, `at/3`, `under/2` | Used by all Prolog recognition rules | Inconsistent bindings / scope mixing | No modification, function-definition anchored audit |
| `for_range/3` and `length_expr/2` | New foundational loop-pattern helpers, reused by outer and inner guards | Assume incorrect `range(len(...))` semantics | Operator/binding/arity checks and mutated AST tests |
| `audited_bubble/4` | New proof-status boundary, user-visible output | False positive from wrong ranges or early exits | Both bounds + shared variables + no abrupt termination |
| `audited_hash/5` | New proof-status boundary | Borrowed/unreachable update, alias effects | Direct update/seed/return, no abrupt exits; still structural only |
| `audited_interleaving/4` | Public cross-thread relation | False association of nearby independent operations | Common function, loop, array and index |
| `audit_classify.pl` | Public output to engineers | Unverified mistaken for absent or proved | Explicit two statuses and disclaimers |
| `test_audit_recognition.py` | Validation gate | Positive-only tests hide false positives | Wrong-bounds and unreachable-update negative controls |

## Residual unsolved risks

1. A code path may be dynamically unreachable for reasons not syntactically visible.
2. `range`, `len` and list methods might be shadowed/overridden; additional semantic/type analysis would be needed.
3. Arbitrary equivalent sorts using alternate loop bounds are intentionally `UNVERIFIED` by this audit; AP7 candidates remain available.
4. Python expressions can have side effects; this is not a complete dataflow or CFG verifier.

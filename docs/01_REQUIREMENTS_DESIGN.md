# AP fallback proof-of-concept: requirements and design (v0.1)

**Goal.** Test, independently of the protected algorithm recognizer, whether
static input/output and local control/data relationships can safely choose
candidate **branches** for later Prolog recognition.

**Non-negotiable:** do not edit/import/run/patch AP9/AP10/AP11; do not modify
TheAlgorithms checkout or SQLite; do not execute unknown candidate Python.

## Inputs, outputs, and decisions

Input: one UTF-8 Python file (at most 1 MB). Parse with stdlib `ast` only.
Output: observable parameter names, return expressions, approximate may-flow
from inputs, line-numbered relationship evidence and SWI-Prolog routes.

Routes are deliberately *not* algorithm identifications:

| Route | Required evidence |
| --- | --- |
| `sequence_rearrangement` | direct input-subscript swap |
| `comparison_driven_reordering` | above, and same-array element comparison controls swap |
| `indexed_lookup` | input-sequence indexed equality against input target controls return of index |
| `interval_lookup` | above, and within one while loop midpoint plus guarded opposing bound updates |
| `unknown` | insufficient supported evidence |

Both parent and child routes may be returned. Mixed algorithms may yield both
reordering and lookup branches in one function. There is no positive `sort`
identity claim in v0.1.

## Pseudocode

```python
parse_source_only(path)             # never import or execute source
for function in top_level_functions:
    inputs = parameters(function)
    rows = walk_supported_statements_and_control_ancestry(function)
    dependencies = approximate_input_to_variable_may_flow(rows)
    outputs = gather_return_sinks(rows, dependencies)
    mutations = detect_direct_input_subscript_exchange(rows)
    comparisons = link_guard_conditions_to_same_array_exchange(rows)
    lookups = link_input_target_equality_to_returned_index(rows)
    intervals = validate_same_loop_midpoint_and_both_updates(rows, lookups)
    emit_fixed_vocabulary_facts_with_line_numbers()
with temporary_fact_file:
    ask_independent_swi_prolog_router(facts)
    show_all_routes_and_unsupported_constructs()
```

## Module responsibilities

- `static_trace.py`: source-only observation, bounded may-dependencies and evidence.
- `run_poc.py`: CLI, safe Prolog fact emission, temporary files, live acceptance.
- `prolog/route.pl`: simple declarative hierarchical routing.
- `examples/`: independent positives and adversarial negatives; never imported.
- `tests/test_trace.py`: offline falsification-oriented regression checks.
- `.cmd`: Windows entrypoints using existing conda and portable SWI-Prolog.

## Critical logic and limitations

| Issue | Protective behavior |
| --- | --- |
| Source execution risks | parse only; never `exec`, `eval`, import candidate, or run it |
| Input→output ambiguity | approximate may-flow only; never advertise semantic proof |
| False sorting detection | require actual reversed two-element exchange on same parameter and controlling comparison of same positions |
| False search detection | demand returned index from same indexed equality to target; interval route needs connected midpoint + two bound writes |
| Dead branch | skip `if False`; stop after unconditional `return`/`raise` within supported lexical block |
| Syntax/code injection | Prolog facts use generated f1/f2 and finite fixed predicate names; no untrusted source strings emitted as executable Prolog |
| Unsupported constructs | report limitations and conservatively stop traversing complex body constructs |
| Cross-function/alias/closure flow | out of scope, do not assume resolved |
| Arbitrary loop correctness | **not proven**; routes are candidate families only |

**Scope:** function-local prototype for direct input subscripting, literal two-element swaps,
indexed-target conditional returns, and two common midpoint formulas. Does not
claim full CFG, program dependence graph, alias resolution, reliable purity,
logical equivalence, actual sortedness, or broad Python coverage. A separate
larger fallback should be considered only after held-out tests show useful routing.

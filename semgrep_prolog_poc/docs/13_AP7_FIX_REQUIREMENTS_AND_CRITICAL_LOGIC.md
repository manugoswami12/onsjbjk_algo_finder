# AP7 Surgical Repair: direct AST statement unification

## Baseline and evidence

* Input: user-uploaded `ap6.zip`, treated as the authoritative baseline.
* Log: `Pasted text(20261009-114944).txt`. AP5 tests pass. AP6 has 9 failures out of 58; all failed expectations require the `rolling_hash_update` match. Bubble sort works.
* The unchanged Semgrep AST encodes direct `Return` statements as immediate children of a function's `Block` statement list. A seed `Assign` is nested under `ExprStmt`.

## Requirements

1. Preserve all AP1–AP6 features, original exact Semgrep AST JSON, AST-to-Prolog exporter and all generated-fact schemas.
2. Recognize a direct `Return` as an event and nested `Assign` inside `ExprStmt` as another event, without forcing them to be represented identically.
3. Do not relax recurrence identity, initialization-before-loop, return-after-loop, other-write rejection, same-function, same-loop, same-array, or same-index constraints.
4. Preserve separate recognition of bubble sort and rolling hash; only report interleaving when the independently identified threads share the same loop, array and index.
5. Preserve UNKNOWN when no validated structural candidate is established.
6. Keep Windows CMD runner, UNIX runner and previous regression tests unchanged, except adding targeted tests.

## Root cause

Original `block_statement_holding/3` used `(Statement == Event ; under(Statement, Event))`. Prolog `==/2` **does not instantiate variables**. When the caller wants to discover the direct `Return` via unbound `Event`, identity cannot succeed; `under/2` cannot return the root statement itself because it only visits descendants. Thus `state_seed_and_return/5` fails and all rolling-hash instances disappear.

## Critical logic table

| Critical component | Why critical (external interface / >2 dependents) | Failure | Fix | Validation |
|---|---|---|---|---|
| `block_statement_holding/3` | Base for thread seed/return, loop discovery; binds Semgrep AST to Prolog variables | `==/2` prevented direct Return discovery | `Event = Statement` OR `under(Statement, Event)` | Direct-return regression + positive and negative tests |
| `state_seed_and_return/5` | Thread identity and temporal constraints | Rejected all valid threads after direct Return vanished | Remains unchanged | Hash positive, missing-return and reset tests |
| `polynomial_recurrence/6` | Operator/variable checks reused by classification | No evidence that arithmetic is wrong | Leave unchanged | Bad multiplier/modulus/self-reference tests |
| `interleaved_sort_hash/4` | Public cross-thread relation, high false-positive risk | Never reached while hash missing | Leave unchanged | Same/different-array, same/different-index, different-function tests |
| `export_ast_facts.py` | External Semgrep JSON to Prolog boundary (>2 consumers) | Working, no defect | Leave byte-for-byte unchanged | Original fact-count/exact exporter tests |
| `thread_classify.pl` and CMD runner | CLI boundary and all report displays | Working | Leave unchanged | Full acceptance suite on user's Windows machine |

## Detailed Python-style pseudocode

```python
for block in ast_nodes_with_tag('Block'):
    for statement in block.direct_statement_children_in_order():
        # A direct statement must be selectable by binding an unknown Event.
        yield event=statement, enclosing_statement=statement
        # A nested statement, e.g. ExprStmt -> Assign, is also selectable.
        for descendant in statement.descendants():
            yield event=descendant, enclosing_statement=statement

for function in parsed_functions:
    for seed in assignments_directly_within(function.body):
        for outer_loop in direct_loops_after(seed):
            for update in recurrent_updates_within(outer_loop):
                for return_stmt in direct_returns_after(outer_loop):
                    if same_accumulator(seed, update, return_stmt):
                        if no_disallowed_writes(function, seed, update):
                            yield rolling_hash_thread(function, outer_loop, update)

for function, region in all_bubble_sort_instances():
    for hash_thread in rolling_hash_threads_in(function):
        if shares_exact_inner_loop_array_and_index(region, hash_thread):
            yield interleaved_sort_hash_relation(region, hash_thread)
```

## Activity grouping and files

| Activity type | Dedicated existing module | Change |
|---|---|---|
| AST environment parsing | `tools/run_demo.py` | None |
| AST data export | `tools/export_ast_facts.py` | None |
| AST and unification traversal | `prolog/thread_rules.pl` | One predicate, one operator correction |
| Recognition and reporting | `prolog/thread_classify.pl` | None |
| Input examples | `examples/*.py` | None |
| Regression tests | `tests/test_thread_recognition.py` | One new direct-return regression |
| User interface/Windows runner | `RUN_AP6_ACCEPTANCE.cmd`, `RUN_THREADS.cmd` | None |

## Verification and limitations

We can run Python-only tests here. Full Prolog and Semgrep acceptance requires the user's Windows installation if `swipl`/`semgrep` are unavailable here. An end-to-end PASS must not be claimed before those tests run. Structural candidate recognition is not semantic proof of a hash or sorting algorithm.

# AP6 Pseudocode, Activity Types, Critical Logic

## Python-like pseudocode (actual execution is deterministic Prolog)

```python
# Existing AP5 stage (unchanged):
json_tree = semgrep_ocaml_dump_ast(source)
prolog_facts = export_all_json_nodes_edges_scalars(json_tree)

# NEW: generic structural navigation over those unchanged facts
for function in all_function_definitions(prolog_facts):
    root_body = function.body
    for outer_loop in direct_or_descendant_for_loops(root_body):
        for inner_loop in nested_for_loops(outer_loop):
            # Thread A: existing bubble-sort rule
            bubble = find_adjacent_gt_and_reverse_tuple_swap(
                inner_loop.body, preserve_array_and_index_bindings=True)

            # Thread B: arithmetic recurrence + its end-to-end state chain
            for assignment in descendants(inner_loop.body):
                match = bind_polynomial_recurrence(
                    assignment.rhs,  # (acc * base + arr[index]) % modulus
                    same_accumulator_on_lhs_and_rhs=True,
                    allowed_operator_tree=['Mod', 'Plus', 'Mult', 'ArrayAccess'])
                if match is None:
                    continue
                assert base > 1 and modulus > base
                assert has_initialization_before_outer_in_function_body(
                    acc=match.acc, value=0)
                assert has_return_after_outer_in_function_body(match.acc)
                assert not_borrowed_from_nested_function(match)
                emit_hash_thread(assignment, match)

            if bubble:
                emit_bubble_instance(outer_loop, bubble)
            for hash_thread in found_hash_threads(inner_loop):
                if bubble and (hash_thread.array, hash_thread.index) == (bubble.array, bubble.index):
                    emit_interleaved_relationship(inner_loop, bubble, hash_thread)

# Output only evidence, never claim mathematical correctness.
# If a proof is missing, output UNKNOWN rather than assert absence.
```

## Activity classification, one program per responsibility

| Activity type | Module | Action |
|---|---|---|
| Source parsing / subprocess, Windows CLI | `tools/run_demo.py` (existing), `RUN_THREADS.cmd` (new) | Reuse external Semgrep and SWI interfaces, add opt-in threads flag |
| Serialization / file I/O | `tools/export_ast_facts.py` | **Frozen**: exact AST JSON -> Prolog nodes/edges/scalars |
| Generic tree navigation | `prolog/classify.pl`, `prolog/ast_regions.pl` | **Frozen**: operators, assignments, function and region membership |
| Existing bubble/binary recognition | `prolog/bubble_rules.pl`, `prolog/multi_classify.pl` | **Frozen** |
| New hash accumulator & relationship inference | `prolog/thread_rules.pl` | State identity, recurrence shape, seed/return order, interleaving joins |
| Console report / Prolog entrypoint | `prolog/thread_classify.pl` | Enumerate and print separately anchored candidates & evidence |
| Test fixtures / regression | `tests/test_thread_recognition.py`, `tests/thread_contract_ast.py` | Positive, negative, cross-function, failure of independent data threads |
| Documentation | `docs/10...`, `docs/11...`, `docs/12...` | Requirements, pseudocode, critical logic, validation handover |

## Critical logic table

Critical means **(1)** environment/other-program interface **or** **(2)** reused as a foundation by more than two code paths.

| Critical site | Why critical | Failure / loophole | Control |
|---|---|---|---|
| Semgrep debug CLI | external executable interface | version-specific AST encoding, failed parse | preserve AP5 command; live external validation |
| Exact JSON fact exporter | external Prolog boundary, used by all recognizers | dropped or changed AST | byte-for-byte unchanged; regression on 783-node fixture |
| `child/3`, `at/3`, `under/2`, `identifier/2`, `operator_call/2` | >2 algorithms depend on them | mis-bound node, duplicated relationship | unchanged AP5 predicates; test AST path and evidence |
| `function_definition/3` and block ordering | >2 consumers and scope guard | evidence borrowed across definitions, seed found in wrong loop | same function body, same direct-block ownership, strict order |
| `rolling_recurrence/..` | core recognition, feeds candidates and relationship | unrelated arithmetic mistaken as hash | require same accumulator, `Mult + ArrayAccess + Mod`, stable constants |
| `thread_state_link/..` | feeds candidates and relationship | uninitialized/unreturned variable, reordered statements | require before/after sibling statements, bound accumulator names |
| `interleaved_sort_hash/..` | feeds relation & user-visible report | two independent loops mistaken as interleaved | share inner loop and array/index, verify distinct update and swap |
| CLI / SWI interpreter / output | external program | masking errors, output stale | explicit source preflight, fixed exit codes, separate opt-in output |
| Test suite and acceptance | environment boundary and regression foundation | tests skip automatically on builder | disclose skips; office acceptance is release gate |

## Explicit interpretation

`rolling_hash_update` is a candidate *structural recurrence*, not a proof of final content hash, security, uniqueness or semantic equivalence. `INTERLEAVED_WITH` means the same inner loop body contains both updating threads. No automatic generalization or invariant inference is included.

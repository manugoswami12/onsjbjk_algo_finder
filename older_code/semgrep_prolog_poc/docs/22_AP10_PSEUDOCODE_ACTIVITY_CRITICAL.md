# AP10 Detailed Pseudocode, Activity Types and Critical Logic

## Pseudocode in execution order
```python
# Read/input environment
reference_code = CLI.argument('learn', label, input_file, function)
ensure_reference_label_is_safe_and_new(label)

# External program interface (only for Python source, not captured JSON)
if input_file.suffix == '.py':
    ast = subprocess.run(['semgrep', 'show', 'dump-ast', '--json', input_file])
else:
    ast = existing_AP9_strict_load(input_file)

# Compilation / file persistence
reference_clause = existing_AP9_compile_reference(ast, label, function, 'body')
save_new_immutable_clause_and_catalog_entry(reference_clause)

# New target code
unknown_ast = semgrep_or_replay_json(target_file)
target_clauses = existing_AP9_compile_candidates(unknown_ast, kinds=('body',))

# Prolog does the actual relational search:
for Reference in all_catalog_reference_patterns():
    for Candidate in target_function_bodies():
        def match(node_ref, node_target):
            if reference_node_is_Block(node_ref):
                # Enumerate order-preserving embeddings of required statements.
                return all_reference_statements_embedded_in_target_Block()
            if both_nodes_are_local_bindings():
                return unify_variable_identity_with_consistent_mapping()
            # All other constructors, keys, operators, literals strictly match.
            return recursively_require_same_ast_constructor_and_children()

        if match(Reference, Candidate):
            verify_reference_bindings_are_distinct_where_required()
            emit('AP10_THREAD', label, target_function, target_region,
                 bindings, concrete_target_loop_paths)

# Composition is separate and strictly evidence-based
for m1, m2 in pairs_of_matches_with_different_labels():
    if m1.function_instance != m2.function_instance:
        continue
    if intersection(m1.concrete_loop_paths, m2.concrete_loop_paths):
        emit('AP10_RELATION', 'shared_loop', concrete_path)
    else:
        emit('AP10_RELATION', 'same_function', 'no shared-loop evidence')
```

## Activity classification and module boundary
| Type | Activity | Module | Why separate? |
|---|---|---|---|
| CLI / input | `learn`, `scan`, validation | `tools/ap10_cli.py` | Human interface only |
| External tool | `semgrep show dump-ast` via subprocess | `tools/ap10_cli.py` | Existing parser, no alternate AST |
| Data compilation | AP9 `compile_reference`, `compile_candidates` | **UNCHANGED** `tools/reference_pattern.py` | Reuse proven translation |
| File saving | Append catalog + immutable `label.pl` | `tools/ap10_cli.py` | Adding knowledge independently |
| Logic/matching | AST structural unification + `Block` subsequences | `prolog/ap10_threads.pl` | SWI-Prolog owns inference |
| Logic/composition | Function and concrete loop-path relations | `prolog/ap10_threads.pl` | No false joins by label alone |
| Testing | independent offline oracle + SWI integration | `tests/test_ap10_composition.py` | Two cross-checks |
| Acceptance | Existing AP9 regression + live `.py` paths | `RUN_AP10_ACCEPTANCE.cmd` | Fail closed |

## Critical-logic review (user's definition)
Critical means (a) environment/other-program interface **or** (b) used by
more than two downstream steps. `YES` flags either criterion.

| Logic | External interface? | >2 consumers? | Critical? | Failure mode and safeguard |
|---|---|---|---|---|
| Semgrep subprocess and AST JSON capture | YES | YES | YES | Exit code, timeout, strict JSON validation, no hidden fallback |
| AP9 `compile_reference` and `compile_candidates` | YES | YES | YES | Reuse byte-for-byte, regression gate |
| SWI-Prolog subprocess and generated clauses | YES | YES | YES | Fail on nonzero; never claim success from Python oracle |
| Exact variable binding and distinctness | NO | YES | YES | Reuse AP9 mapping and `distinct_binding_names/1` |
| AST `Block` subsequence handling | NO | YES | YES | Narrow allowance, never omit required reference statements |
| Loop AST path evidence | NO | YES | YES | Compare concrete target paths, not reference loop names |
| Catalog I/O and immutable labels | YES | YES | YES | Reject duplicate labels, path-safe clause names |
| CMD status / acceptance | YES | NO | YES | Real positive outputs explicitly asserted, errorlevel checked |
| Formatting explanatory output | NO | NO | NO | Clearly state STRUCTURAL only |
| Demo comments and examples | NO | NO | NO | Not used for detection |

## Known counterexamples, deliberately NOT hidden
- If the inserted statement reassigns a required variable, this simple
  syntactic matcher may still match. It does **not** prove data-flow integrity.
- A wrong but structurally identical algorithm may match: our result is a
  reference-structure resemblance, not a correctness certificate.
- Reordered required statements, `for` changed into `while`, helper calls,
  aliasing, or algorithms split across functions can produce false negatives.
- Two matching loops in mutually exclusive branches are not necessarily
  simultaneously executed; `shared_loop` reports AST location only.

Any follow-on work on these cases needs its own proof and separate opt-in module.
Do not quietly weaken this matcher to pretend such problems are solved.

# AP3 pseudocode, responsibilities, and review plan

## Detailed Python-style pseudocode (design, not a new Python AST parser)

```python
# Existing tools/export_ast_facts.py: UNMODIFIED
ast_json = semgrep_ocaml_dump(source)
facts = exact_JSON_tree_flatten(ast_json)  # all nodes, all ordered edges

# tools/run_demo.py: AP2 contract kept, new --multi selects Prolog entrypoint
opts = parse_args(original_options + ["--multi"])
check_paths_and_external_binaries(opts)
clear_outputs_before_run()
if opts.ast_json: copy_replay_fixture_preserving_contents()
else: run_semgrep_show_dump_ast_json_with_timeout()
run_standard_library_fact_exporter_with_timeout()
if opts.multi:
    run_swipl('prolog/multi_classify.pl', goal='main_multi')
else:
    run_swipl('prolog/classify.pl', goal='main')

# prolog/ast_regions.pl: generic structural relationships
for function_def in prolog_query_ast_tag('DefStmt'):
    function_name, function_body = decode_definition_function(function_def)
    for region in recursively_find_function_body_regions(function_body):
        if tag(region) in {'For','While'}:
            yield (function_def, function_name, region)

def strict_before(region1, region2, function_body):
    return exists_block_containing_both_as_direct_siblings(region1, region2) \
           and numeric_sibling_index(region1) < numeric_sibling_index(region2)

# prolog/bubble_rules.pl: no variable names/labels inferred from filename
for outer_loop in nodes_tagged('For'):
    for inner_loop in nested_for_nodes(outer_loop):
        for if_node in nodes_in_loop_body(inner_loop):
            condition = test_expression(if_node)
            a, j = indexed_operand_of_greater_than(condition)
            assert other_operand == array_index(a, plus(j,1))
            body = then_branch(if_node)
            for assignment in assignments_inside(body):
                lhs_pair = immediate_indexed_pair(lhs(assignment))
                rhs_pair = immediate_indexed_pair(rhs(assignment))
                assert lhs_pair == [a[j], a[j+1]]
                assert rhs_pair == [a[j+1], a[j]]
                yield (outer_loop, evidence)

# prolog/multi_classify.pl: no suppression of other algorithm instances
for function in function_defs():
    matches = setof((algorithm, region_id, evidence),
                    all_binary_regions(function) | all_bubble_regions(function))
    print_each_match(matches)
    for (first, second) in pairs_of_matches(matches):
        if strict_sibling_order(first.region, second.region):
            print_relationship(first.algorithm, 'BEFORE', second.algorithm)
    if no_matches: print_unknown(function)
```

## Activity grouping: one coherent program per task
| Activity | Module | Reads | Writes |
|---|---|---|---|
| Parse/CLI, source checks, temp output, subprocess | `tools/run_demo.py`, `RUN_MULTI.cmd/.sh` | Python file or JSON fixture | `out/ast.json`, process status |
| AST serialization (no algorithm names) | existing `tools/export_ast_facts.py` | JSON | exact `out/facts.pl` |
| Shared Prolog AST navigation, function membership and ordering | `prolog/ast_regions.pl` | AP2 generic facts | query relations |
| Bubble sort candidate rule | `prolog/bubble_rules.pl` | generic query relations | `bubble_instance/3` |
| Binary search candidate rule | existing `prolog/classify.pl` + AP3-scoped rule | generic facts | `binary_instance/3` |
| Multi-hit enumeration and reporting | `prolog/multi_classify.pl` | bubble and binary predicates | console results |
| Regression/acceptance | `tests/test_multi_recognition.py` plus all existing tests | real/contract fixtures | PASS/FAIL, no silent skips on office PC |
| Design & handover | `docs/04_*.md`, `docs/05_*.md`, `README.md` | design and test evidence | acceptance instructions |

## Failure handling
- Keep exact AST even if neither recognizer matches.
- Do not infer internal sort implementation from `sorted()` invocation.
- Reject classification if swap side identities are not reversed.
- Don't merge evidence from different functions or loops.
- Print candidate label with qualification rather than claiming semantic proof.
- Preserve preexisting AP2 `main` predicate and runnable commands.
- In the absence of real external binaries, report tests skipped rather than claim end-to-end success.

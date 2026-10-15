# Requirements -> pseudocode -> module/activity grouping

## Detailed executable design in Python-like pseudocode

```python
# parse/run layer, tools/run_demo.py
source = resolve_cli_source_or_default()
require(source.is_file() or replay_ast_file.is_file())
require(swipl_is_on_path())
if replay_ast_file is None:
    require(semgrep_is_on_path())
remove_stale_generated_outputs()
if replay_ast_file is None:
    run_semgrep_ocaml_dump_ast(source, ast_json_output, timeout=60)
else:
    copy_preexisting_semgrep_json(replay_ast_file, ast_json_output)
require_success_and_nonempty_ast()
run_existing_stdlib_exporter(ast_json_output, prolog_facts_output)
require_success_and_nonempty_facts()
run_swipl_with_classification_rules_and_facts(timeout=60)
propagate_error_code_and_print_the_Prolog_answer()

# JSON conversion layer, tools/export_ast_facts.py
parsed = json.loads(semgrep_json)
stack = [(parent=None, value=parsed, edge_label='root')]
groups = {'ast_edge': [], 'ast_tag': [], 'ast_scalar': []}
while stack:
    parent, value, edge_label = stack.pop()
    allocate_stable_node_id_preorder()
    reject_if_more_than_100000_nodes()
    if parent: groups['ast_edge'].append(edge(parent, current_id, edge_label))
    if is_object(value):
        if len(value) == 1: emit_tag(constructor); push('value', payload)
        else: emit_tag('record'); push_each_field_in_reverse_order()
    elif is_array(value):
        emit_tag('list'); push_array_positions_in_reverse_order()
    else:
        emit_tag('scalar'); emit_scalar_as_safely_quoted_atom(value)
write_headers_then_each_group_contiguously_then_ast_node_count()

# semantic layer, prolog/classify.pl (relational pseudocode)
read ast_tag, ast_edge, ast_scalar facts
child(P, K, V) = ast_edge(P, V, K)
constructor_payload(C) = child(C, 'value', P)
array_position(C, N) = child(constructor_payload(C), str(N), E)
operator_call(Call, Kind, Args) =
    Call tagged 'Call' AND first argument tagged 'Special'
    AND embedded 'Op' contains scalar Kind AND second argument is array Args

while_parts(While, Condition, Body) =
    While tagged 'While' AND its [1] element tagged 'Cond'
    AND its [2] element tagged 'Block'

candidate(binary_search) = exists While, LowName, HighName, MidName, ValuesName, TargetName:
    while condition is Call(op='LtE', id(LowName), id(HighName))
    AND body contains assignment
        id(MidName) = Call(op='FloorDiv',
                           Call(op='Plus', id(LowName), id(HighName)), integer(2))
    AND body contains If condition
        Call(op='Eq', ArrayAccess(id(ValuesName), id(MidName)), id(TargetName))
    AND that If's then-branch returns id(MidName)
    AND body contains assignment id(LowName) = Call(op='Plus', id(MidName), integer(1))
    AND body contains assignment id(HighName) = Call(op='Minus', id(MidName), integer(1))
print_candidate_and_evidence_else_unknown()
```

## Activity grouping (one program per coherent type)

| Category | Requirements / pseudo-steps | Owner | Interface |
|---|---|---|---|
| External tools + file orchestration | Source validation, Semgrep subprocess, SWI subprocess, timeouts, fresh output | `tools/run_demo.py` | filesystem, CMD, Semgrep CLI, SWI CLI |
| Generic JSON -> Prolog facts, safe persistence | Deserialize JSON, flatten, quote atoms, group clauses, count nodes, write output | `tools/export_ast_facts.py` | AST JSON and Prolog facts |
| AST navigation + reasoning | Navigate variant/list shapes, read operator scalars, match scoped program structure | `prolog/classify.pl` | 4 generic fact predicates |
| User command entrypoints | CMD/Linux invocation without feature removal | `RUN_DEMO.cmd`, `RUN_DEMO.sh` | Python command |
| Validation | JSON shape, escaped strings, negative controls, optional real SWI/Semgrep executions | `tests/*`, `RUN_SELFTESTS.cmd` | stdlib unittest + optional executables |
| Documentation / output | Requirements, pseudocode, compatibility and manual commands | `docs/*`, `README.md` | human text |

## Critical-logic review (user's two criteria)

Critical means (1) interface to environment or another program, OR (2) reused as the foundation of >2 downstream parts. The items below are critical and must receive focused tests.

| Critical component | Why | Baseline problem | Safeguard + test |
|---|---|---|---|
| Semgrep CLI dump interface | External binary | Debug JSON evolves by version | Replay real uploaded 783-node dump; reject bad/non-JSON and command failure |
| JSON-to-Prolog scalar quoting | External interpreter + core primitive | Backslash/quote injection or invalid atoms | Escaping test for Unicode, quotes, slashes, newline |
| AST node/edge preservation | Base for all rule predicates | Losing child order or node IDs breaks semantic matching | Stable preorder IDs, indexed edges; round-trip structure tests |
| Prolog fact grouping | External SWI loader | Thousands of `discontiguous` warnings | Group clauses by predicate + compatibility declarations |
| OCaml `Op` representation | Used in midpoint, loop condition, branch, updates | Original matcher sought nonexistent `Plus`/`Div` tags | Operator-path facts tests on captured JSON |
| Generic AST identifier and int paths | Reused in >2 algorithm conditions | Different OCaml wrappers from anticipated | Variable identity and literal extraction tests |
| Scope and variable unification | Base for several matching conditions | Accidental matches across loops/functions | Bind one loop and same names in all subpatterns; negative mutation tests |
| Subprocess termination + fresh results | Environment interface | Stale positive could appear after failed Semgrep | Remove old outputs, exit nonzero on failure and timeout |

## Review criteria

* Do not rename/remove baseline functions or CLI commands.
* No user-supplied input should be executed as Prolog source other than properly quoted data atoms in generated facts.
* Negative control must not contain a midpoint/interval-narrowing match.
* Detailed output should avoid giant warning streams.
* Prolog result is a candidate, not a proof, and must not be described as complete equivalence.

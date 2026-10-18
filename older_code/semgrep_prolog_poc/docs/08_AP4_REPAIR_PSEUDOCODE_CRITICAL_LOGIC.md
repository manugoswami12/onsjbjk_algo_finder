# Repair algorithm, activity classification, and critical-logic review

## Stepwise pseudocode (Python-like, but execution is Prolog)

```python
# The exporter remains unchanged.
for node in exact_semgrep_ast_facts:
    if tag(node) != 'DefStmt':
        continue
    entity = variant_item(node, 0)
    name_node = child(entity, 'name')             # EN variant
    name = extract_id_name(name_node)              # preserve original spelling
    kind = variant_item(node, 1)                   # FuncDef variant
    if tag(kind) != 'FuncDef':
        continue
    kind_fields = variant_value(kind)              # **real Semgrep record**
    fb_stmt = child(kind_fields, 'fbody')           # FBStmt variant
    body = variant_value(fb_stmt)                  # Block variant
    if tag(body) != 'Block':
        continue
    yield (node, name, body)

# Existing Prolog recognizers are intentionally reused without modification.
for definition, name, body in function_definitions():
    candidates = distinct(existing_binary_regions(definition) +
                          existing_bubble_regions(definition))
    print_evidence(candidates)
    for left, right in direct_sibling_order(candidates, body):
        print('BEFORE', left, right)
```

## Activities grouped by behavior

| Activity | Component | Existing / new | Why distinct |
|---|---|---|---|
| External CLI calls, JSON and file I/O | `tools/run_demo.py`, `tools/export_ast_facts.py` | Unchanged | Environment boundary; keep single command authority |
| Exact AST graph navigation | `prolog/classify.pl` primitives and `prolog/ast_regions.pl` | Surgical change only to function discovery | Shared foundation for >2 algorithm/region predicates |
| Algorithm region recognition | `prolog/classify.pl`, `prolog/bubble_rules.pl`, `prolog/multi_classify.pl` | Unchanged rules | Separate classification from discovery |
| Reporting | `prolog/multi_classify.pl` | Unchanged output | Stability for callers and tests |
| Validation | `tests/test_multi_recognition.py` plus new contract tests | Extended | Detect actual Semgrep encoding failure in independent fixture |
| Documentation | `docs/07...`, `docs/08...`, `docs/09...` | New | Audit trail, reproducibility |

## Critical logic (criterion: environment interface OR foundation of >2 consumers)

| Critical site | Why critical | Original problem/risk | Mitigation and tests |
|---|---|---|---|
| Semgrep subprocess `dump-ast --json` | External tool / protocol | Format version drift; no live Semgrep here | Existing live tests on office PC; fixture contract test |
| JSON → Prolog serializer | File boundary, fact base for every rule | Loss of node identity or labels | Leave unchanged; fixture fact count equals AP2 1,833 lines |
| `child/3`, `value/2`, `at/3`, `under/2` | Shared by all recognition logic | Incorrect variant traversal | Validate exact record/variant graph |
| `function_definition/3` | Shared by bubble, binary, ordering, output (>2 consumers) | **Missing `value` edge beneath FuncDef** | Repair one predicate; real Semgrep fixture test |
| Prolog load and `main_multi` | External executable / output contract | Silent `UNKNOWN` and warning floods | Test expected text and absence of warning |
| `algorithm_before/5` | Relationship backbone for multiple regions | Cross-function order false positive | Separate-functions negative test |
| Structural discriminators | User-facing recognition | Overmatching superficial nested loops | Swap/comparison mutated negatives; candidate labeling |

## Acceptance

Windows: `RUN_AP3_ACCEPTANCE.cmd` followed by `RUN_MULTI.cmd examples\\sort_then_search.py`. Required: 35+ successful tests, 2 correctly located candidates in the mixed function, a `BEFORE` relation, negative controls, and no SWI warnings. If any fail, capture the first failure plus AST JSON, not only the terminal `UNKNOWN`.

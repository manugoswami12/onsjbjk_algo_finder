# AP9 implementation plan, detailed pseudocode, activity grouping and critical logic

## Python-style pseudocode
```
parse_json_lossless(path):
    read input as UTF-8 with optional BOM
    json.loads(text, parse_int=JsonNumber, parse_float=JsonNumber,
               parse_constant=reject, object_pairs_hook=reject_duplicate_keys)
    return JSON tree retaining numeric literal lexemes

typed_export(tree):
    baseline_lines = existing_flatten(tree)   # unchanged exact AP8 contract
    traverse same stable preorder node IDs:
        emit ast_json_type(Node, object|array|string|number|boolean|null)
        for object: emit ordered UTF8/base64 keys for each child
        for scalar: emit UTF8/base64 scalar payload
    write baseline_lines plus grouped typed lines to SEPARATE file

typed_reconstruct(facts):
    parse only restricted generated fact syntax (never eval/consult untrusted facts)
    rebuild nodes by preorder edges and typed field-order records
    decode base64 strings and numeric tokens with custom JsonNumber
    verify original JSON VALUE equals reconstructed JSON VALUE

compile_reference(captured_ocaml_ast, label, function, region, ordinal):
    locate exact DefStmt→FuncDef→fbody in the *Semgrep JSON*
    collect function's explicit local bindings and parameter names
    choose region by Semgrep constructor and ordinal; do not guess algorithm
    project AST: remove ONLY nonsemantic OCaml Id/PatId info payload,
                 parameter pinfo and token placeholders kept as literal
    replace bound local identifier occurrences by repeatable slot markers
    keep free/global identifiers, literal strings, numeric constants and operators
    render static reference_pattern(Label, Kind, Term). with Prolog variables
    save reference Prolog file, and a JSON manifest with reference attribution

compile_target(captured_ocaml_ast):
    enumerate each function and its candidate regions, same projection rules
    render candidate_pattern(Function, Path, Kind, GroundTerm).

match_in_prolog:
    load generic Prolog engine, generated reference + generated target
    for each reference_pattern, candidate_pattern:
        require same region kind and unify AST Terms
        report only actual successful matches, with source function/region
        print 'REFERENCE_STRUCTURAL_MATCH', never 'ALGORITHM_PROVED'
    when no match: UNKNOWN, never a guaranteed negative semantic judgment

evaluate(manifest):
    compare expected labels with matched reference outputs
    count TP/FP/FN/TN, precision and recall; list failures
    do NOT claim general zero error from a bounded test set
```

## Activity groups → one module each
| Group | Inputs/outputs | Module |
|---|---|---|
| Strict JSON reading / lossless export / reversible decode | OCaml JSON ↔ typed facts | `tools/typed_ast_codec.py` |
| Region selection / stable projection / rule generation | JSON → generated reference/target `.pl` | `tools/reference_pattern.py` |
| Generic unification / result formatting | generated `.pl` files → match evidence | `prolog/reference_match.pl` |
| User CLI / environment / file saving | Windows CMD and Python args | `tools/run_reference.py`, `RUN_AP9_*.cmd` |
| Dataset evaluation / metrics / report | manifest + captures → JSON report | `tools/evaluate_reference.py` |
| Offline and live regression | fixtures + executables | `tests/test_ap9_*.py` |

## Critical-logic table
Critical = interfaces with environment or other programs, OR a foundation used by more than two dependent operations.
| Logic | Critical reason | Failure and safeguard |
|---|---|---|
| Strict JSON loading and duplicate-key rejection | Foundation (export, reconstruction, matching, tests) | Silent data loss; reject invalid/ambiguous JSON |
| Stable node traversal and ordered edges | Foundation (AST facts, source regions, decoder, matcher) | Incorrect node identity; deterministic counter and roundtrip tests |
| UTF8/base64 encoding and decoded type reconstruction | Foundation (all scalar reconstruction and tests) | Type collision or injection; strict parsing, exact UTF8 roundtrip |
| Semgrep function-body extraction | Foundation (reference and target, scope and evidence) | Cross-function matches; explicit DefStmt/FuncDef/fbody path checks |
| Binder-aware projection | Foundation (compiler, matcher, evaluation) | False positive from renamed global or false negative on locals; literal globals and repeated-slot tests |
| Prolog text escaping and generation | External SWI interpreter interface | Injection / syntax errors; quote escaped atoms and never eval user text |
| Semgrep subprocess, SWI call, path resolution | External binaries/OS | False success after failure; strict return code, timeout, no stdin piping |
| Score computation | Foundation (FP/FN/TP/TN, precision, recall) | Misleading accuracy claims; preserve per-case evidence and zero-divisor status |

# AP2: Semgrep OCaml generic AST -> Prolog recognizer

## Scope and baseline (9 October 2026)

The user supplied `ap1.zip`, an existing one-file proof of concept. Keep the exact source path: **Python source -> Semgrep's OCaml `AST_generic` -> JSON -> Python standard-library fact exporter -> SWI-Prolog**. Do NOT replace Semgrep with Python's `ast`, add another parser, alter the user's frozen CodeGraph or ACE pipeline, remove any existing command, or add third-party Python libraries. Preserve `ast_tag/2`, `ast_edge/3`, `ast_scalar/2`, `ast_node_count/1` and source fixtures.

Evidence from actual uploaded `out/ast.json`: 783 nodes were extracted. Semgrep encodes `x + y` as `Call` with `Special([Op:"Plus", ...])`; operators `Plus`, `FloorDiv`, `LtE`, etc. are **scalar values below an `Op` constructor**, not tags `ast_tag(_, 'Plus')`. The old rule therefore could not match. The exporter interleaved predicate clauses, producing repetitive SWI-Prolog discontiguous warnings.

## Acceptance criteria

1. Baseline commands `RUN_DEMO.cmd` and `RUN_DEMO.cmd examples\search_linear.py` continue to work without source-code modifications or administrator rights. On Linux, `RUN_DEMO.sh` remains.
2. `out/ast.json` preserves Semgrep JSON exactly (normal live command) and `out/facts.pl` remains complete generic tree facts. No hardcoded algorithm label in the exporter.
3. Fact output groups predicates so loading does not emit discontiguous warnings. Preserve node IDs, parent edges, field indexes, scalar escaping, node count, and safety limit.
4. Prolog matcher follows the actual Semgrep OCaml AST shape, enforces consistent loop-bound and midpoint variable identities, both bound updates and indexed-target comparison **inside the same while loop**. It must not rely on the function name or source text.
5. The real positive dump in `tests/fixtures/semgrep_binary_ast.json` must produce `CANDIDATE: binary_search`; a structurally altered negative fixture and the live linear-search example must produce `UNKNOWN`.
6. The runner may replay a previously captured AST via `--ast-json` (avoids re-downloading/installing Semgrep for diagnosis), but the existing normal run always invokes Semgrep.
7. Return nonzero on malformed JSON, missing tools, failed subprocess, invalid Prolog fact generation, or timeout. Do not silently classify stale output.
8. No academic claim of equivalence or formal proof. Output `candidate`, with evidence and limitations.

## Data interfaces (version sensitive)

- Input Python program: Semgrep CLI `semgrep show dump-ast --json <file>`; internal JSON is Semgrep debug representation, subject to version changes.
- `out/ast.json`: arbitrary nested JSON objects/lists/strings/numbers/booleans/null; no Python AST parsing.
- `out/facts.pl`: four predicates (`ast_tag/2`, `ast_edge/3`, `ast_scalar/2`, `ast_node_count/1`). List child labels are strings `'0'`, `'1'` etc.; constructor values use the edge label `'value'`.
- Query: `swipl -q -f none -s prolog/classify.pl -s out/facts.pl -g main -t halt` (existing SWI interface).

## Design choice

Implement structural relations **in Prolog** (OCaml generic-AST recognizer). Python code is restricted to deterministic JSON flattening, IO and subprocesses. Group generated facts by predicate; add compatibility `discontiguous` declarations in Prolog for old files.

## Non-goals

Arbitrary algorithm equivalence, complexity proofs, interprocedural data flow, sortedness verification, full algorithm-library classification, control-flow soundness, or recognition of all binary-search idioms. This v2 recognizes an explicit inclusive-bound binary-search family only. A false positive remains possible; candidate is deliberately qualified.

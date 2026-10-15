# AP9 acceptance, freeze boundary and remaining verification

## What was actually built
- New `tools/typed_ast_codec.py`: strict parser with duplicate-key rejection, raw number token retention, ordered base64 UTF8 scalar/keys, fully reversible JSON-value fact extension. AP8 original facts remain untouched.
- New `tools/reference_pattern.py`: deterministic compiler from Semgrep OCaml AST reference body/loop/statement to static Prolog `reference_pattern/4`; target projection into ground `candidate_pattern/4`. User labels reference; Python does not infer algorithm semantics. Names of bound locals are Prolog variables repeated consistently, free names/operators/constants literal.
- New `prolog/reference_match.pl`: generic SWI-Prolog unification and distinct-binding constraints; scoped evidence and machine reporting.
- New `tools/run_reference.py`: accepts actual Python `.py` via Semgrep or previously captured Semgrep JSON. Strict error and timeout behavior.
- New `tools/evaluate_reference.py`: independent confusion matrix, default real SWI-Prolog execution, optional Python oracle for local preflight; no successful report if executables missing.
- New tests and fixtures, Windows CMD wrappers and previous-doc preservation.

## Observed local environment results (Linux container, no swipl/semgrep)
- AP9 expanded `python -m unittest discover -s tests -q`: 102 tests, 50 passed, 52 skipped, 0 failed (run BEFORE potential final new regression).
- Strict type roundtrip: genuine captured Semgrep binary AST, 783 nodes, PASS; scalar string/number/bool/null and object/list cases PASS.
- Deterministic generation and rename / changed operator / changed constant / changed builtin / variable conflation controls pass in independent Python oracle.
- Built-in bounded 10-case dataset: 4 TP / 0 FP / 0 FN / 16 TN in Python **oracle**, not yet SWI-Prolog. Two user-labeled reference templates. One reference is a captured real binary-search Semgrep AST; the second is a synthetic mutation of a captured real AST (this provenance is explicit).
- **SWI-Prolog compiled term execution and `.py`→Semgrep source runs NOT YET locally validated**. Do not freeze AP9 until the user's Windows `RUN_AP9_ACCEPTANCE.cmd` is green and machine report agrees.

## Required Windows sequence
1. Extract AP9 into a NEW folder. From project root with `ons_ruleskg` active run `RUN_AP9_ACCEPTANCE.cmd`.
2. Confirm all AP8 regressions remain green; confirm `test_ap9_*` SWI live tests run without skips.
3. Confirm `out\ap9\evaluation.json` reports `backend: prolog`, counts 4/0/0/16, `all_expected_results_match=true`.
4. Run `RUN_AP9_REFERENCE.cmd examples\search_binary.py examples\search_binary.py my_reference locate_item body` to demonstrate actual live Semgrep conversion and generated Prolog matching.
5. Inspect saved generated `reference.pl` and `candidate.pl`. They must contain no manually written algorithm-specific matching predicate. Label is explicit from CLI.

## False positive/negative policy
"No errors" is only claimed relative to the finite, defined alpha-renamed exact structural equivalence benchmark. A different implementation of the same algorithm can produce a false negative relative to *semantic* equivalence; a structurally matching program can be incorrect on unmodeled inputs. Compiler and evaluator NEVER claim universal semantic classification.

## Critical external risks
- Semgrep OCaml AST JSON layout may change across Semgrep versions. Unsupported layouts stop or return no structural match; never invent algorithm meaning.
- Local name resolution is conservative (parameters, PatId, simple local assignments). Python dynamic binding, nested scopes, comprehensions and attributes are NOT a complete SSA/data-flow analysis.
- Large ASTs create large Prolog terms; 100k node cap applies to typed facts. Scope region compilation and timeouts bound external execution.
- SWI-Prolog syntax/roundtrip needs Windows runtime validation since `swipl` unavailable locally.

## AP8 preservation assertion
AP8 baseline contains 71 non-cache files. In AP9 exactly 70 are **byte-for-byte unchanged**; the sole modified legacy file is the append-only `README.md` explaining AP9 commands. The original `tools/export_ast_facts.py`, all preexisting Prolog rules, and every AP8 CMD runner are byte-for-byte unchanged.

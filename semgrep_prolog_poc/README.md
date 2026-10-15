# AP2: Semgrep OCaml generic AST -> SWI-Prolog algorithm recognition

This is the surgical repair of `ap1.zip` (9 October 2026). Existing features,
examples, public Prolog predicates, Windows/Linux demo runners and JSON-tree
fact format remain available. **No changes to any CodeGraph, ACE, or Wren files.**

```
Python source -> Semgrep's OCaml parser -> AST_generic JSON
              -> Python stdlib fact exporter -> SWI-Prolog rules
              -> Candidate algorithm + evidence / UNKNOWN
```

The Python helper uses **`json`, not Python's `ast`**. Semgrep's OCaml engine
performs source parsing. Prolog performs the actual algorithm recognition.

## First read the design

- `docs/01_REQUIREMENTS_DESIGN.md`: baseline, requirements, interfaces and acceptance criteria.
- `docs/02_PSEUDOCODE_ACTIVITY_MATRIX.md`: detailed pseudocode, activity/module split, critical-logic review table.

## Install (Windows, no admin rights needed for the PoC itself)

Requires Python 3.10+, `semgrep` and the `swipl` binary on PATH. The user
already has Semgrep and a portable SWI-Prolog installation on their office PC.
A portable SWI-Prolog executable may be in `A:\swipl\bin\swipl.exe`:

```cmd
set "PATH=A:\swipl\bin;%PATH%"
semgrep --version
swipl --version
```

Adjust the SWI-Prolog directory if your executable is elsewhere. No WSL is
required. Semgrep can be installed with `python -m pip install semgrep`.

## Run (Windows CMD, from extracted ZIP folder)

```cmd
RUN_DEMO.cmd
RUN_DEMO.cmd examples\search_linear.py
RUN_SELFTESTS.cmd
```

Expected on the first command (live Semgrep, supplied positive example):

```text
AST nodes exported: ...
CANDIDATE: binary_search
Evidence: loop ...; midpoint ...; indexed comparison ...; both bound updates
Limit: candidate only; no semantic-equivalence proof
```

Expected on the second command (live Semgrep, linear-search negative control):

```text
UNKNOWN: no algorithm signature matched
```

Reproduce using the **actual 783-node Semgrep AST captured in the user's upload**,
without rerunning Semgrep:

```cmd
RUN_DEMO.cmd --ast-json tests\fixtures\semgrep_binary_ast.json
```

Note: SWI-Prolog is still required for the replay command. On Linux, use
`./RUN_DEMO.sh` and `./RUN_SELFTESTS.sh`.

The runner generates `out/ast.json` and `out/facts.pl`. The latter contains
four original public fact predicates:

```prolog
ast_tag(Node, Constructor).
ast_edge(Parent, Child, FieldOrIndex).
ast_scalar(Node, Value).
ast_node_count(Count).
```

Clauses are grouped by predicate to avoid `discontiguous` warning floods.
Original AP1 files are also accepted by the repaired classifier.

## What changed from AP1?

**Problem 1:** The 783-node dump showed the real Semgrep JSON operator
representation: `Call [ Special [ Op:"FloorDiv", ... ], [Arg(...), ...] ]`.
There are no `ast_tag(_, 'FloorDiv')` facts. Prolog now resolves the `Op`
**scalar** in its actual structural path.

**Problem 2:** The old recognizer only searched vaguely for division, a `2`,
and comparisons anywhere under the loop. It did not enforce the same lower,
upper and midpoint variables. The new rule unifies all three across the loop
condition, midpoint assignment, array indexed comparison, return statement
and both bound updates **inside the same while body**.

**Problem 3:** The fact writer mixed different predicate clauses, causing
thousands of Prolog warnings. Facts are now grouped but losslessly preserve
the original graph node IDs and edge indexes.

## Testing

`RUN_SELFTESTS.cmd` uses only Python's standard-library `unittest`. There are
three tiers:

1. Pure exporter/AST-contract tests that run everywhere (including this build
   environment).
2. Real SWI-Prolog tests driven by the uploaded 783-node AST; automatically
   skipped only if `swipl` is absent.
3. Full Semgrep -> Prolog positive and linear-search negative tests; skipped
   only if either executable is absent.

The actual downloaded AST is bundled at
`tests/fixtures/semgrep_binary_ast.json`, not a made-up Python AST fixture.
No label is inferred from the filename or the function name.

## Honest boundaries

- This is a **candidate** recognizer for one common, inclusive-bounds iterative
  binary-search form. It is not a proof of sortedness, termination, or
  semantic equivalence and does not cover every binary-search implementation.
- It does not yet perform full CFG, SSA or symbolic-equality inference.
- `semgrep show dump-ast --json` is a debug CLI with version-sensitive
  `AST_generic` serialization; new Semgrep shapes should be added to the
  Prolog adapter and backed by real AST fixtures.
- Nothing is copied into or merged with the frozen `codegraph.json`.

For baseline discussion of the Semgrep OCaml generic AST command, see
https://github.com/semgrep/semgrep/blob/develop/src/osemgrep/cli_show/Show_subcommand.ml.

## AP3 extension: two algorithms in one Python function

AP3 adds an **opt-in**, exact-AST-backed multi-region recognizer while leaving
AP2's `RUN_DEMO.cmd` and legacy `candidate/1,2` interface unchanged.
Read `docs/04_AP3_REQUIREMENTS_DESIGN.md`, `docs/05_AP3_PSEUDOCODE_ACTIVITY_MATRIX.md`,
and `docs/06_AP3_VALIDATION_HANDOVER.md` before running the upgraded mode.

In the original CMD directory:

```cmd
RUN_SELFTESTS.cmd
RUN_MULTI.cmd examples\sort_then_search.py
RUN_MULTI.cmd examples\sort_only.py
RUN_MULTI.cmd examples\no_swap_then_search.py
```

The `sort_then_search.py` case contains **both** a nested-loop adjacent swap
(bubble sort) and a binary search in the same `find_number` function. AP3
enumerates separately anchored AST regions and reports `bubble_sort BEFORE
binary_search` only when those region roots are ordered direct siblings of
a real AST `Block`.

The API is `algorithm_instance(FunctionName,Algorithm,Region)` and
`algorithm_before(Definition,AlgoA,RegionA,AlgoB,RegionB)`. It can be queried
interactively after consulting `prolog/multi_classify.pl` and the freshly
generated `out/facts.pl`.

**Limits:** This is still a structural *candidate* detector, not automatic
mathematical proof or broad algorithm-learning. It accepts one specific
bubble-sort form and the existing inclusive-bounds binary-search form. It
retains the exact AST facts instead of rewriting them into a reduced feature
set. The OCaml AST dump is version-sensitive. Live multi-algorithm acceptance
must pass on the office computer before marking AP3 frozen.

## AP6 (opt-in): interleaved sorting and rolling-hash logic threads

AP6 builds on the **unchanged AP5 exact AST fact schema and existing binary / bubble recognition**. Read `docs/10_AP6_REQUIREMENTS_DESIGN.md` and `docs/11_AP6_PSEUDOCODE_ACTIVITY_CRITICAL_LOGIC.md` first.

Run in your already-working `ons_ruleskg` Windows CMD with `semgrep` and `swipl` on PATH:

```cmd
RUN_AP6_ACCEPTANCE.cmd
RUN_THREADS.cmd examples\interleaved_sort_hash.py
RUN_THREADS.cmd examples\interleaved_wrong_input.py
RUN_THREADS.cmd examples\interleaved_no_swap.py
```

The positive example performs an adjacent bubble swap and an independent
polynomial digest update **inside the same repeated inner loop**. AP6 joins the
threads only if they share the same array and index and the hash accumulator
is initialized beforehand, updated recursively in the loop and returned later.

Expected positive labels (node IDs vary with exact source):

```text
CANDIDATE: bubble_sort; function: inspect_items; AST region: ...
CANDIDATE: rolling_hash_update; function: inspect_items; AST region: ...
RELATION: rolling_hash_update INTERLEAVED_WITH bubble_sort; function: inspect_items; regions: ...
```

Additional negative controls: `interleaved_no_hash_recurrence.py` (different
RHS accumulator), `interleaved_no_swap.py` (no sorting),
`interleaved_wrong_input.py` (two threads but different arrays, no relation),
`interleaved_reset_digest.py` (broken state chain), and
`interleaved_separate_functions.py` (never mix evidence across functions).

This is deliberately a **narrow structural candidate** for a polynomial
rolling-hash *update*. It is not proof of semantic equivalence, correctness,
collision resistance or sorted-output fingerprinting. Unsupported variants
remain `UNKNOWN`; no change to `RUN_MULTI.cmd`, `RUN_DEMO.cmd`, or legacy
Prolog predicates. No Popper / ML / invariant discovery / generalized-pattern
learning. Do not freeze until live Windows tests pass without skips.

## AP8 conservative audit (opt in)

The AP7 matchers and exact Semgrep AST facts are unchanged. AP8 adds stricter
*structural audit* checks for canonical bubble-sort bounds and a directly
executed rolling-hash recurrence. Existing `--threads` mode behaves exactly
as before.

```cmd
RUN_AP8_ACCEPTANCE.cmd
RUN_AUDIT.cmd examples\interleaved_sort_hash.py
RUN_AUDIT.cmd examples\audit_wrong_bounds.py
RUN_AUDIT.cmd examples\audit_dead_hash.py
```

The audit prints `audited_structural`, `unverified` (with **audit blockers**),
or `legacy_candidate` for not-yet-audited algorithms. `INTERLEAVED_AUDITED`
is emitted only when two independently audited strands share loop, array,
and index bindings. An `unverified` finding is **not** evidence of incorrect or
absent code. These checks are syntactic, not semantic proofs. See
`docs/15_AP8_REQUIREMENTS_DESIGN.md`, `docs/16_AP8_PSEUDOCODE_CRITICAL_LOGIC.md`,
`docs/17_AP8_VALIDATION_HANDOVER.md`.

## AP9 deterministic reference-pattern compiler (opt in)

**AP8 remains frozen.** AP9 adds separate tools and never modifies AP8's
`tools/export_ast_facts.py`, original `out/facts.pl`, or algorithm recognizers.

### Step 1: confirm JSON-value losslessness

```cmd
RUN_AP9_TYPED.cmd tests\fixtures\semgrep_binary_ast.json
```

`out\ap9\typed_facts.pl` contains original AP8 facts **plus** new typed
`ast_json_type/2`, `ast_json_key64/3`, `ast_json_scalar64/2` facts. Numbers retain
literal exponent/negative-zero spelling; booleans, null and strings are distinct.
Decode uses the documented Python `decode_typed()` function. "Lossless" means
the JSON **value and ordered object keys**, not byte-for-byte source whitespace
or string escape formatting. Duplicate object keys cause a hard error.

### Step 2: automatically generate a labeled Prolog pattern and match

From **already captured Semgrep OCaml JSON** (works offline with SWI-Prolog):

```cmd
RUN_AP9_REFERENCE.cmd tests\fixtures\ap9_cases\binary_exact.json tests\fixtures\ap9_cases\binary_renamed.json binary_search_reference locate_item body
```

Or directly from **Python source** (requires Semgrep + SWI-Prolog, runs real
`semgrep show dump-ast --json` on both files):

```cmd
RUN_AP9_REFERENCE.cmd examples\search_binary.py examples\search_binary.py binary_search_reference locate_item body
```

The reference algorithm label is **supplied by the user**. No classifier
magically invents whether the reference is sorting, hashing, searching, etc.
Python generates `out\ap9\reference.pl` and `out\ap9\candidate.pl`. Generic
`prolog/reference_match.pl` unifies the compiled AST terms and reports
`REFERENCE_STRUCTURAL_MATCH`, the target function/region, and bound variables.
**Do not confuse that with a semantic proof.**

Region selector: `body`, `for`, `while`, `if`, `assign`. Whole `body` means an
exactly structured function body with consistent locally renamed identifiers.
Selecting `for` can find a reference loop inside another function containing
unrelated surrounding statements. It does not infer data-flow semantics.
Free/global identifiers, operators, constants, and relative statement order
stay literal. AST metadata used only for Semgrep's inference/binder IDs is
excluded in the **separate matching projection**, not in original facts.

### Step 3: inspect false-positive/false-negative results

```cmd
RUN_AP9_EVALUATE.cmd
```

This runs real SWI-Prolog on 10 declared test cases, saves
`out\ap9\evaluation.json` and counts TP, FP, FN, TN per reference label ×
function. Current offline-only Python-oracle preflight passes 4 TP / 16 TN;
Windows execution **must** verify the SWI-Prolog results independently.

### Step 4: full regression acceptance

```cmd
RUN_AP9_ACCEPTANCE.cmd
```

AP8 tests remain available through `RUN_AP8_ACCEPTANCE.cmd`. Detailed
requirements, pseudocode and critical-logic review are in
`docs/18_AP9_REQUIREMENTS_DESIGN.md`, `docs/19_AP9_PSEUDOCODE_ACTIVITIES_CRITICAL.md`,
`docs/20_AP9_VALIDATION_HANDOVER.md`.

### Why this is not "no false positives/negatives" for arbitrary Python

Exact structural equivalence (up to the supported local alpha-renamings) is a
decidable contract and can be tested with no errors. Arbitrary code with the
same semantics but different structure may be missed; a deliberately misnamed
or incorrect reference may mislead the user-provided label. Keep the existing
AP8 audited structural recognizers and do not promote these template matches
to mathematical proof.

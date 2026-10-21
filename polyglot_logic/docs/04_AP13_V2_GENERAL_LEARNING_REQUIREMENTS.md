# AP13 v2 Requirements and Design: learn from ALL algorithms (15 October 2026)

## 1. User objective
"It learns from all algorithms and uses that knowledge to identify various
algorithms in other languages."

AP13 v1 learned only bubble sort and binary search, and only functions with
three kinds of output: element swaps, element writes, and returns inside loops.
v2 must:

- learn **every** function of TheAlgorithms/Python, pinned at commit
  `e1a2a8b0`, 1,608 files and 4,648 functions;
- identify algorithms written in Rust, Java, C, R, Haskell, Common Lisp and
  Prolog against that learned knowledge;
- be **measured** on a large held-out set written by other people.

## 2. Constraints (unchanged from doc 01)
- Separate folder.
- No frozen AP2–AP12 file is edited, and no v1 feature is removed.
- The v1 acceptance tests A1–A8 stay green.
- Deterministic: no ML and no Popper.
- Matching is never loosened. Generality comes from:
  - more general *tracing*, so more programs produce logic facts;
  - more *canonical forms*, so different spellings give equal logic;
  - *more references*, learned automatically.
- Standard library first. The only additions are tree-sitter-language-pack and
  SWI-Prolog.

## 3. Measured gaps that v2 must close
| Gap (measured on the corpus) | Count | v2 answer | Established basis |
|---|---|---|---|
| Outputs that v1 does not trace (accumulator returned after a loop, recursive results, yields, appends) | most functions | general **output set** (G1) | slicing criterion = all outputs (Weiser) |
| Recursion in imperative languages (quicksort, merge sort, factorial, gcd, Hanoi) | many | a self-call is a recursion loop; recursive arguments are parameter updates (G2) | recursion/iteration correspondence; SDG (Horwitz–Reps–Binkley) |
| Docstrings | 3,541 | ignored | — |
| `raise`/`assert`, `break`/`continue` | 2,049 / 333 | early-exit control dependence (G6) | PDG control dependence (Ferrante–Ottenstein–Warren) |
| `for x in s` vs `for i in range(len(s))` vs list recursion vs `foldl` | many | **element-iteration canonical form** (G4, G5) | Metzger & Wen canonical forms |
| Helper-function names differ across languages | many | calls to functions defined in the same file are variabilised (G7) | alpha-renaming (AP9 slots) |
| Tiny helpers (`return a + b`) would match everything | many | **reference quality gate** (G8) | precision first |
| Many references match one candidate | — | **most-specific-first ranking** and grouping of structurally identical references (G9) | subsumption ordering |
| One swipl process per function is too slow for 4,648 functions | — | one swipl process per file (G10) | — |

## 4. Design decisions
- **G1 Outputs.** The effects of a function are:
  - exchanges;
  - writes to an element of a parameter, or of a returned local;
  - appends (`append`, `push`, `add`, `push_back`, `cons` onto a result);
  - returns and yields of non-constant values, inside or outside loops.
- **G2 Recursion.**
  - A function that calls itself gets a `recursion` loop containing all its statements.
  - The self-call is named `$self`.
  - Its arguments become `assign(param_k, arg_k)` updates, as Haskell and Prolog already do.
  - So recursive gcd `gcd(b, a % b)` and iterative `a, b = b, a % b` produce the same logic.
- **G3 Data slice.** Definitions that reach slice variables and lie inside *any* loop of the function are followed. Initialisation outside loops is still left out (0- vs 1-based indexing).
- **G4 Element iteration.** "The current element of sequence `s` in loop `L`" is one canonical term, `elem(s, var(V))` with `lvar(L, var(V))`. It covers:
  - `for x in s` (x is rewritten to `elem(s, x)`);
  - `for i …: s[i]`;
  - Haskell/Prolog `x:rest`;
  - folds.
- **G5 Folds.** These become a loop with an accumulator:
  - Haskell `foldl`, `foldl'`, `foldr` with a lambda or named function;
  - Lisp `reduce`;
  - R `Reduce`;
  - Python `functools.reduce`.
- **G6 Early exits.** `return`, `raise`, `break`, `continue` (and Lisp `return-from`). Statements after `if c: <exit>` are guarded by `not c`.
- **G7 Names.**
  - Calls to functions defined in the same source become variables in learned references.
  - Library calls keep their canonical names. A synonym table maps, for example: `ord` = `fromEnum` = `char-code` = `charCodeAt` → `ord`; `abs`; `sqrt`; `max`; `min`.
- **G8 Quality gate.** A reference is *usable* only if it has at least one loop or recursion relation and at least 4 relations. Smaller references are stored with status `trivial` and never used for matching.
- **G9 Ranking.**
  - All matches are reported, most specific (most relations) first.
  - Structurally identical references (same clause up to variable renaming, `variant_sha1`) form one group.
  - The identification is the top group's source path and function.
- **G10 Scale.** `learn-dir DIR` learns every function of every file, with one swipl call per file. It is idempotent, with sha-256 per pattern. `learn-corpus` (AP11 catalog) stays.
- **G11 Evaluation.** The ground truth `benchmark/rosetta_truth.json` is written **before** the run:
  - Rosetta task → the TheAlgorithms files that implement it;
  - tasks without a counterpart are negatives.

  Metrics:
  - top-1 correct;
  - any-correct;
  - top-1 wrong (false identification);
  - UNKNOWN.

  Results are reported per language and per task. No per-file tuning: the
  benchmark files are never edited.

## 5. Acceptance criteria (v2)
| Id | Criterion |
|---|---|
| B1 | v1 tests A1–A8 still pass |
| B2 | `learn-dir` on the whole corpus finishes, reporting generated / trivial / no_effects / error counts with none hidden; a rerun is idempotent |
| B3 | Every learned reference is variabilised, sha-checked, and traceable to `path::function` |
| B4 | Rosetta evaluation over ≥ 30 tasks × 8 languages runs to completion with all metrics reported, including false identifications |
| B5 | Top-1 false identifications are reported with the reference that caused them; if precision is low the result is stated, not hidden |
| B6 | Existing frozen suites unchanged |

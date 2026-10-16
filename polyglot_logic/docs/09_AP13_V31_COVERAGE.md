# AP13 v3.1: an explained outcome for every file (16 October 2026)

## 1. Requirement and decisions
**The request** was 100% precision, 100% recall and 100% coverage.

**Joint 100% is impossible on this held-out set.** Measured before this work, of 789 files:
- 181 files have no function at all: script fragments, usage lines, imports.
- 156 files have a function with no loop or recursion: library calls and one-liners.

**User decisions:**
- Build the honest maximum.
- **Coverage** = files with an explained outcome.
- A file with no algorithm body counts as covered when the tool says exactly that.
- Precision target ≥ 95% on algorithm answers.
- Recall pushed toward the ceiling.
- The test half is untouched until the end.

## 2. Outcomes (one per file; judging rules frozen in `benchmark/rosetta_outcome_note.md`)
| Outcome | Meaning | In precision / recall? |
|---|---|---|
| IDENTIFIED | unchanged exact matcher, full cover (doc 07) | yes |
| FAMILY | family answer with ≥ 2 levels; helpers excluded (one answer per file) | yes |
| LIBRARY | a library call that **is** the algorithm (`sort`, `gcd`, `lcm`, `factorial`, `bisect`, `isleap`) | yes |
| SHAPE | input→output shape only (`sequence_query`, `numeric`, …) | no: own accuracy shown |
| AMBIGUOUS | answers in different top-level families: all kept, none claimed | no |
| CONTAINS | the function does more than a reference explains | no |
| NO_ALGORITHM_BODY | no definition in the **source** (parse tree), or only straight-line code / calls, and no higher-order combinator | no (covered) |
| UNKNOWN | traced but no branch, unmodelled construct, definitions not lowered, or combinator not modelled, with the reason | no (not covered) |

## 3. Established basis (in addition to doc 08)
- **One answer per file.** The topmost algorithmic function, i.e. a call-graph root among the functions that have a family. Helpers are listed, never the answer. This is the program-plan view of Wills/GRASPR.
- **Library idioms count only when they are the result.** As in LLVM LoopIdiomRecognize, an idiom replaces the computation, so incidental calls (`max` in a printer) are not identifications.
- **Conflicting evidence keeps all branches and claims none.** This is the fallback rule of the 14–15 Oct discussion: "Multiple plausible families → preserve all plausible branches".

## 4. Pseudocode (`tools/outcome.py`)
```python
def classify(file):
    facts = lower(file)
    if exact_match(file):                 return IDENTIFIED      # unchanged cli.scan
    deep, shape = family_answers(file)                           # family_scan.answers
    if top_levels(deep) > 1:              return AMBIGUOUS
    if deep:                              return FAMILY
    if shape:                             return SHAPE
    if contains(file):                    return CONTAINS
    if strong_library_call(facts):        return LIBRARY
    if no_lowered_function and source_has_definitions(file):
                                          return UNKNOWN('definitions present but not lowered')
    if no_loop_or_recursion and combinator_called(facts):
                                          return UNKNOWN('higher-order combinator not modelled')
    if no_loop_or_recursion and nothing_unmodelled(facts):
                                          return NO_ALGORITHM_BODY(reason)
    return UNKNOWN(reason)
```

## 5. Activities and programs
| Type | Program |
|---|---|
| Outcome and evaluation (user input, display) | `tools/outcome.py` (new) |
| Static data | `tools/library_families.py` (new) |
| Logic (new branches, beacons, single answer) | `prolog/roles.pl`, `prolog/families.pl` (v3 files extended) |
| Accessor normalisation | `prolog/family_main.pl` (`charAt`, `car`/`cdr`, `remove-if-not`) |
| Own cases | `examples/v3/cases/c23…c36`, `expected_families.json`, `expected_outcomes.json` |

No v1, v2 or v2.1 file is changed.

## 6. Critical logic
| Logic | Why critical | Risk | Safeguard |
|---|---|---|---|
| `answer_function/1` | decides which function speaks for the file | a helper's family taken as the answer | call-graph root among functions with a family; test on pancake/flip and on helpers |
| NO_ALGORITHM_BODY | the coverage claim | claiming "nothing to trace" where the lowerer failed | definitions counted on the parse tree; combinators make it UNKNOWN; R27 below |
| SHAPE | coverage | shape conflicts with the method family (Levenshtein is list→value but table-fill DP) | never counted as an algorithm answer; its accuracy is reported |

## 7. Problems found while measuring (dev half, then one test run)
| # | Observation | Cause | General fix |
|---|---|---|---|
| R1 | `flip` (uncompared reversal) reported for a pancake sort | every function's family was the file's answer | one answer per file: call-graph roots with a family |
| R2 | in C, `mx = i` became `mx := 1` | `i++` in a `for` header is not an assignment fact; copy propagation used the initial value | the most-wanted role also reads the raw `assign` (family layer only) |
| R3 | run-length encoding also an element-wise map | the append of `count + s[i]` | a map visits every element: its index is the loop variable |
| R4 | LIBRARY right in only 10 of 45 dev files | `max`, `sum`, `index`, `reverse` in helpers and printing | only strong names; weak names were wrong even when returned |
| R5 | factorial "wrong" while the reference is a factorial | graded on the first label only | graded on the whole structural group, as `rosetta_eval` does |
| R6 | cocktail sort "is a palindrome test" | `a[i]` vs `a[i-1]` taken as a mirror | a mirror is `n-1-i`: `i` is the subtrahend |
| R7 | DP (`dp[j] = max(dp[j], dp[j-w]+v)`) an element-wise map | the map rule read other elements | reads only its own element, no `min`/`max`; needs a `mod`/`xor`/`ord`/`chr` shift |
| R8 | heap sort "uncompared" | the comparison is in the sift-down helper | compared-anywhere also checks the called local functions |
| R9 | heap sort "selection" | `largest = left` is a most-wanted holder | selection needs the holder to take the scan's loop variable |
| R10 | the shape level dropped precision from 88.7% to 66.0% | the shape contradicts method families (Levenshtein, functional quicksort) | SHAPE is its own outcome; never an algorithm answer |
| R11 | functional quick/merge sorts "queries" | they read a list and return a NEW list | the query or numeric shape needs a scalar result |
| R12 | the scalar-result check looped forever | `x = x + …` | bounded depth |
| R13 | one sieve given three families | contradicting evidence | AMBIGUOUS: candidates kept, none claimed |
| R14 | heap sort beacon missed | `child = 2*root + 1`, then `a[child]` | the beacon follows one assignment, and the helper's evidence belongs to the caller |
| R15 | **85 Haskell files "no algorithm body"** | definitions not lowered; combinators (`map`, `iterate`, `mapAccumL`) | NO_ALGORITHM_BODY only if the parse tree has no definitions and no combinator is called; else UNKNOWN with the reason |
| R16 | the Lisp fragment's reason claimed a call the tracer cannot see | Lisp top-level forms are not lowered | the reason says so ("top-level forms of this language are not traced") |

## 8. Measured results (frozen 789 Rosetta files, r9 validated catalog)
**Own cases:** 32/32 family cases and 6/6 outcome cases are correct. They are development data.

| | Dev half (tuned on) | **Test half (one run)** | All |
|---|---|---|---|
| Coverage (explained outcome) | 79.5% (after R15: lower) | **67.1%** (267/398) | 68.1% (537/789) |
| Precision (IDENTIFIED + FAMILY + LIBRARY) | 93.1% (95/102) | **85.9%** (67/78) | 90.0% (162/180) |
| Recall (correct / positive files) | 25.7% | **18.3%** (66/360) | 22.0% (158/718) |
| Wrong on negatives | 0 | 2 of 38 | 2 of 71 |
| SHAPE answers (not counted above) | 97 (48 agree) | 112 (52 agree) | 209 (100 agree) |

**All 789 files by outcome:**

| Outcome | Files (correct) |
|---|---|
| IDENTIFIED | 36 (35) |
| FAMILY | 138 (121) |
| LIBRARY | 6 (6) |
| SHAPE | 209 |
| AMBIGUOUS | 5 |
| NO_ALGORITHM_BODY | 143 |
| UNKNOWN | 252 |

**Against the targets:**
- **Precision ≥ 95%:** not reached on the test half (85.9%). It is 93.1% on dev, the gap typical of tuning on dev.
- **100% coverage:** not reached (67.1% on test). Every UNKNOWN carries a stated reason:
  - a traced loop or recursion with no branch;
  - definitions present but not lowered;
  - a combinator not modelled;
  - an unmodelled construct.
- **Recall:** 18.3% on test.

| Recall level | Value |
|---|---|
| Exact identification alone (doc 07) | 6.4% |
| Exact + family, one answer per file (this work) | 22.0% on all files |

## 9. What limits recall (with examples)
1. **Same task, different algorithm.** `Fibonacci-sequence/Python/…-1.py` uses Binet's closed form, so there is no recurrence to trace.
2. **No algorithm in the file.** `Leap-year/Python/…-1.py` is `calendar.isleap(year)` (LIBRARY). `Greatest-common-divisor/Python/…-1.py` is `from math import gcd` (NO_ALGORITHM_BODY). Haskell `ghci> take 15 fibs` transcripts are the same.
3. **Lowering gaps.** Haskell `where` blocks and point-free equations, combinators (`iterate`, `zipWith`, `mapAccumL`), Prolog accumulator predicates and Lisp `loop … collect` produce no traced loop. These are the largest UNKNOWN groups (R15).
4. **Branches still missing**, or shapes that contradict the taxonomy: Levenshtein is "list→value" by I/O but table-fill DP by method.

**The next step with the largest effect** is lowering, not branching: model Haskell `where`/point-free definitions and the higher-order combinators as loops. That is the same fold expansion that `fact_io.expand_folds` already does for `reduce`/`foldl`. It is a change to working lowerers, so it needs the user's approval.

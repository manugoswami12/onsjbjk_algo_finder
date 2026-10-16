# AP13 v3: input→output family branching (16 October 2026)

## 1. Why
**Recall was low because of the branching** (doc 07 §6, user review, 16 Oct).

**What the branching was:**
- The only family router was the frozen AP12 `route_extended.pl`. It has two families: sequence_rearrangement → comparison_driven_reordering, and indexed_lookup → interval_lookup.
- So almost all 1,794 learned references sat in one flat `unknown` branch.
- A program that missed every strict leaf got UNKNOWN, even when its input→output trace showed what kind of algorithm it is.

**What the agreed fallback design said** (ChatGPT discussion of 14–15 Oct, lines 859–1102, 3078, 3602):
- Trace input→output.
- Let Prolog branch from broad to narrow: small variations reach small branches, large variations stop at broader branches.
- Never loosen acceptance.
- With no leaf match, report the narrowest supported family.
- Measure the family level and the exact level separately.

## 2. Constraints
- **The working code is not touched.** Everything is added beside it:
  - new Prolog files load the unchanged `main.pl`, which brings canon, slice, evidence, leaf and the frozen AP12 router;
  - new Python modules call the unchanged `cli.py` functions.
- Deterministic, static, and no execution. No ML.
- A family answer is a **candidate category, never an identity claim**. Exact identification stays as in doc 07.

## 3. Established basis
| Source | Used for |
|---|---|
| Sajaniemi, *roles of variables* (stepper, gatherer, most-wanted holder, follower, organizer, one-way flag) | `role/3` in `roles.pl`: language-independent behaviour of each variable |
| Taherkhani (Computer Journal 2011; ICPC'10; PPIG 2012): decision tree over roles plus "beacons" recognises sort and search families at about 97–98% | the tree shape (roles → family → leaf) and beacon idioms (heap index `2i+1`, gap exchange, partition, merge) |
| Chains of recurrences (Bachmann, Wang, Zima 1994), LLVM ScalarEvolution `{start,+,step}` | `rec_class/3`: counter vs accumulation vs pair / modulo / conditional recurrence |
| LLVM LoopIdiomRecognize; Ginsbach and O'Boyle, CGO 2017 (reductions and histograms) | `idiom/3`: reduction, histogram (counting sort), strided store (sieve), table fill |
| Program slicing and chopping, PDG/SDG (Weiser; Horwitz, Reps, Binkley), as in the AP12 fallback | input→output shape, one-level interprocedural sequence parameters |
| AP12 `observed/3` + `route/2` (this repo, 11/11 live tests) | reused **unchanged** for the sort and lookup decisions |

## 4. Family tree (broad → narrow)
```
sequence_transformation
  comparison_sort      adjacent_exchange | shift_insertion | select_extreme | partition_recursive
                       | merge | gap_exchange | heap | stooge_recursion        (else: comparison_sort)
  distribution_sort    histogram
  uncompared_rearrangement
sequence_query
  target_search        interval_halving | linear_scan                          (else: target_search)
  aggregate            gatherer | most_wanted
numeric
  recurrence           pair_recurrence | modulo_recurrence | range_accumulation | double_recursion
  decomposition        digits
  divisor_test | conditional_iteration | predicate
marking                stride_marking | table_fill
```
- Only the deepest supported paths are reported; a path that is a prefix of another is dropped.
- A function may have several paths (mixed code).

## 5. Pseudocode
```python
def families(source):                                  # tools/family_scan.py
    facts = cli.facts_text(source)                     # unchanged lowering
    return prolog('family_main', facts)                # prolog/family_main.pl

# family_main.pl
load_data(facts); normalise_accessors()                # elt/aref/nth/car/cdr -> elem/tail (family layer only)
assert_observations()                                  # unchanged AP12 evidence
for f in functions:
    roles  = role(f, R, X)                             # organizer, stepper, gatherer(op), most_wanted, follower(y)
    recs   = rec_class(f, C, X)                        # pair, modulo, range_accumulation, digits, conditional,
                                                       # divisor_test, double_recursion
    idioms = idiom(f, I, X)                            # histogram, stride_marking, table_fill, index_return,
                                                       # midpoint, compared_rewrite, shift, partition, merge,
                                                       # adjacent, gap, heap, stooge
    paths  = [p for p in family_path(f)]               # rules over route/2 + roles + recs + idioms
    print deepest(paths)
```

## 6. Activities and programs (one per type)
| Type | Program | Status |
|---|---|---|
| Logic: roles, recurrences, idioms | `prolog/roles.pl` | new |
| Logic: branch rules | `prolog/families.pl` | new |
| Entry and accessor normalisation | `prolog/family_main.pl` (loads `main.pl` unchanged) | new |
| Environment and file interface | `tools/family_scan.py` (calls `cli.facts_text`, `env_run.swipl`) | new |
| Development check (own cases) | `tools/family_cases.py` + `examples/v3/expected_families.json` | new |
| Held-out evaluation | `tools/family_eval.py` (reuses `rosetta_eval.files`) + `benchmark/rosetta_family_truth.json` | new |
| User input | `RUN_AP13_FAMILY.cmd/.sh` | new |

## 7. Critical logic
Critical means it interfaces with another program, or is the base for more than two others.

| Critical logic | Why critical | Risk | Safeguard |
|---|---|---|---|
| `seq_param/2` (is a parameter a sequence?) | splits sequence vs numeric for every function | a functional sort looking numeric | sequence uses `elem`, `tail`, `filter`, `map`, `len`, fold iteration, plus one interprocedural level |
| `role/3` stepper vs gatherer | base for recurrences, aggregates and sorts | a counter taken for an accumulator | `counter/2` (`x = x ± c`) from `slice.pl` |
| `exclusive/2` + `follows/2` for double recursion | decides linear vs tree recursion | alternative branches or clauses counted as two calls | calls must be in one statement sequence and not under opposite guards |
| accessor normalisation | interfaces with the Lisp lowerer output | an over-broad rename | family layer only; fixed list (`elt aref svref nth car cdr rest first …`) |
| `family_eval` grading | the reported numbers | a lenient grade inflating precision | strict precision (every path must agree), the lenient figure shown beside it, a dev/test split |

## 8. Problems found while measuring
Development used the 22 own cases and the **dev** half of Rosetta; the **test** half was not used for tuning.

| # | Observation | Cause | General fix |
|---|---|---|---|
| F1 | Lisp linear search had no family | `(elt seq i)` stays a call in the Lisp lowerer | the family layer rewrites accessor calls to `elem/2` / `tail/2` |
| F2 | Collatz also reported as "digits" | `n div 2` with `n mod 2` | digit decomposition needs the remainder as **data** (in a value), not only in a test |
| F3 | helpers (`safe(a, b)`) became "numeric predicate" | one comparison was enough | ≥ 2 tests over arithmetic on a parameter, no delegation |
| F4 | comb and shell sort called "adjacent exchange" | AP12 comparison_driven_reordering is not adjacency | adjacent `i, i+1` vs gap `i, i+g` (variable `g`) vs heap `2i+1` beacons |
| F5 | stooge sort called quicksort | "two recursive calls + an exchange" | in-place partition needs a compared exchange inside a loop (or a local partition function); stooge is ≥ 3 calls, no loop |
| F6 | counting sort with an offset was missed, and also reported as a generic comparison sort | index `a[i] - min`; parent and leaf in different subtrees | histogram index *contains* an input element; the comparison-sort parent is suppressed by a distribution sort |
| F7 | functional quick/merge sorts looked "numeric" | sequence use seen only through `elem/2` | `seq_use/2` (tail, filter, map, len, loop iteration) |
| F8 | in-place quicksort looked "uncompared" | the exchange is controlled through a loop over the pivot | uncompared requires that **no** element of the sequence is compared anywhere in the function |
| F9 | perfect numbers also reported as factorial-like | a guarded divisor sum looks like an accumulation | range accumulation must be unconditional |
| F10 | Roman numerals reported as Collatz-like | `n -= v` under alternatives | conditional iteration needs a multiplicative branch |
| F11 | Towers of Hanoi had no family | the recursive calls are statements, not a returned value | double recursion also from two call statements |
| F12 | after F11, recursive binary search and Haskell/Prolog code became "double recursion" | calls in alternative branches or clauses | both calls on one statement sequence (`next_stmt`), not exclusive |
| F13 | sieve with a set (`multiples.update(range(i*i, n+1, i))`) missed | marking through a collection call | a collection receiving a strided range of the loop variable |
| F14 | merge sort had no branch | — | merge beacon: a comparison of elements of two different sequences decides which is taken next |

## 9. Measured results (same frozen 789 Rosetta files, 8 languages)
Family truth `benchmark/rosetta_family_truth.json` was written from each task's textbook class **before** the first family run.

**Own cases:** 22/22 correct, no contradicting path. The own cases are development data.

**Family level** (`tools/family_eval.py`):

| Split | Strict precision | Lenient precision | Recall | Of which at the exact leaf |
|---|---|---|---|---|
| first run, before any tuning (all) | 60.4% | 67.0% | 15.5% | 106 |
| dev, after F1–F14 | 89.3% (75/84) | 90.5% | 19.4% | 68 |
| **test (not used for tuning)** | **80.0% (60/75)** | 84.0% | **15.8%** | 59 |
| all | 84.9% (135/159) | 87.4% | 17.6% | 127 |

- The test half was looked at once, only to locate the F12 regression (alternative clauses). F12 is a general rule.
- Exact level, unchanged (doc 07): precision 97.2% (35/36), recall 6.4% with library calls.

**Combined answer:** the exact identification when one exists, else the family.

| Metric | Value |
|---|---|
| Precision | 85.2% (138/162) |
| Correct, out of all 789 files | 17.5% |
| Exact recall alone, for comparison | 6.4% |

**What is still missing:**
- Branches with no rule yet: palindrome, Caesar / element-wise map, run-length, N-queens / backtracking, Roman numerals / greedy denominations, cycle sort, pancake sort.
- Fragments and library-only files.
- Some Haskell and Prolog list idioms.

Each new branch should be added the same way: an own case first, then dev, then a single run on test.

## 10. How to run
```
RUN_AP13_FAMILY.cmd <source file>                 # families of every function
python tools/family_cases.py                      # the own cases
python tools/family_eval.py --rosetta <clone> --split test
```

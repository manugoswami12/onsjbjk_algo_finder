# Cross-language test, stage 1 (3 cases per language): FAILED, stage 2 not run

Knowledge learned from 395 labelled Python files; tested on Rosetta Common-Lisp and Haskell (seeded samples frozen in crosslang_truth.json). Channels: AP13 learn-dir (exact traced logic) + AP13 io_catalog (behaviour).

| Language | Precision | Recall | Wrong on negatives |
|---|---|---|---|
| Common Lisp | no answers (0/0) | 0/2 | 0/1 |
| Haskell | no answers (0/0) | 0/3 | 0/0 |

Why: Lisp gcd-3 calls an undefined gcd2 (bug in the Rosetta entry), so its behaviour cannot be computed; Lisp lcm-2 uses &rest + reduce + lambda, which the Lisp-to-Prolog translator does not support; Haskell has no behaviour translator, and the exact traced-logic references learned from Python never match Haskell equations (stooge sort, list-comprehension sieve, binary search).

```
file                                                         expected                     outcome   routes  [learner]
Task/Greatest-common-divisor/Common-Lisp/greatest-common-divisor-3.lisp euclid_like                  UNKNOWN   -  
Task/Knapsack-problem-0-1/Common-Lisp/knapsack-problem-0-1.lisp None                         ok(neg)   -  
Task/Least-common-multiple/Common-Lisp/least-common-multiple-2.lisp euclid_like                  UNKNOWN   -  

Common-Lisp sample 3
PRECISION = correct / answered = 0/0 = 0.0%
RECALL    = correct / positives = 0/2 = 0.0%
WRONG ON NEGATIVES = 0 of 1
file                                                         expected                     outcome   routes  [learner]
Task/Sorting-algorithms-Stooge-sort/Haskell/sorting-algorithms-stooge-sort-2.hs comparison_driven_reordering UNKNOWN   -  
Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-23.hs sieve_like                   UNKNOWN   -  
Task/Binary-search/Haskell/binary-search-3.hs                ['interval_lookup', 'indexed UNKNOWN   -  

Haskell sample 3
PRECISION = correct / answered = 0/0 = 0.0%
RECALL    = correct / positives = 0/3 = 0.0%
WRONG ON NEGATIVES = 0 of 0

[exited with code 0]
```

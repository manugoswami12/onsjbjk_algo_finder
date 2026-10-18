# Cross-language test on kaveet/haskell-snippets and Apress/programming-algorithms-lisp

Knowledge learned only from labelled Python (TheAlgorithms 232 + Rosetta Python 163 + 1 extra reference).
Function-level keys frozen first (`crosslang_ext_truth.json`); each inspected sample retired before the next.

## Code checks before testing
- ruff (F, B, PLE, PLW, RUF012, ...) and pylint (E, W): clean, 10.00/10. mypy: only AST attribute accesses
  behind helper-function guards. semgrep registry rules: not reachable from this environment.
- Logic error found by ruff RUF012: shared mutable class state in the Haskell converter (fixed).
- Differential test `tests/test_frontends.py`: 10 Haskell + 12 Lisp programs run natively (GHC, SBCL) and through
  the front end; all outputs equal. It found and pinned: GHC overload-wrapper arity; Lisp `(return)` inside loops
  (base translator returned from the function); `&optional` parameters (base translator ignored the caller's
  argument); calls whose value is unused were dropped (lost side effects); comparator parameters.

## Results
| Language | Stage | Precision | Recall | Wrong on negatives |
|---|---|---|---|---|
| Haskell | stage 1, sample 1 (3 fns) | 1/1 | 1/2 | 0/1 |
| Haskell | stage 1, sample 2 (3 fns) | 2/2 = 100% | 2/2 = 100% | 0/1 |
| **Haskell** | **all 11 functions** | **4/4 = 100%** | **4/6 = 66.7%** | **0/5** |
| Common Lisp | stage 1, samples 1-6 | no answers | 0/1, 0/2, 0/1, 0/1, 0/1, 0/2 | 0 wrong in all |

Haskell misses: `fib` (fib 0 = 1 convention, measured before the shift-matching change), `sum` (no plain
list-sum reference in TheAlgorithms; the added product_sum reference is not runnable by the AP13 Python translator).
Lisp misses (each diagnosed): comparator parameters, wrapper credit, `(return)`/`&optional`/dropped-call
translator bugs (all fixed, but found on those samples), Fibonacci index convention (shift match added), 2-D
matrix input (`mat-max`), `nil` vs `-1` for absent search targets (`bin-search-v0`), RUTILS displaced slices
(`quicksort`). No wrong answer was produced in any run.

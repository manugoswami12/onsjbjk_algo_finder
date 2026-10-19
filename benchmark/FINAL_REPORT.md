# Final report (doc 04 section 18.5)

Reporting criteria (final_report.py): bad code is ignored. A held-out file is not analysable when the pipeline gave it no answer and none of its root functions runs on every battery input; a wrong answer is never excluded. Identical TheAlgorithms files are one alias group. All-files numbers are kept beside the analysable-only ones. The main pipeline is unchanged; the class answers come from the separate fallback (eval_decision.py, v0.3 runner, node witness).

## Learnt code: TheAlgorithms/Python

| files | not analysable (no algorithm code) | scored | correct | false positives | false negatives | precision | recall (analysable) | recall (all files) |
|---|---|---|---|---|---|---|---|---|
| 1346 | 2 | 1344 | 1344 | 0 | 0 | 100.0% | 100.0% | 99.9% |

- not analysable: web_programming/crawl_google_results.py, web_programming/open_google_results.py (an `if __name__ == '__main__'` block only)
- alias groups (identical logic, either label right): 3 files: ciphers/base58.py = base58 / base64_cipher; ciphers/base64_cipher.py = base58 / base64_cipher; conversions/int_to_negative_binary_base.py = base_neg2_conversion / int_to_negative_binary_base
- false negatives: none
- false positives: none

## New code: held-out Rosetta files (never learned from)

| language | files | not analysable (excluded) | scored | correct | false positives | false negatives | precision | recall (analysable) | recall (all files) |
|---|---|---|---|---|---|---|---|---|---|
| C | 69 | 34 | 35 | 32 | 0 | 3 | 100.0% | 91.4% | 46.4% |
| Common-Lisp | 75 | 29 | 46 | 45 | 0 | 1 | 100.0% | 97.8% | 60.0% |
| Haskell | 144 | 102 | 42 | 33 | 1 | 9 | 97.1% | 78.6% | 22.9% |
| Python | 162 | 79 | 83 | 66 | 4 | 17 | 94.3% | 79.5% | 40.7% |
| all | 450 | 244 | 206 | 176 | 5 | 30 | 97.2% | 85.4% | 39.1% |

False negatives = scored files without a correct answer (wrong ones included).

### Why files are not analysable (all languages)

- a root does not run on every input: 160
- no run: 53
- no root function: 28
- output does not depend on the input: 3

### The false positives (all from the main pipeline; the fallback made none)

- Task/Least-common-multiple/Python/least-common-multiple-2.py: Greatest-common-divisor (algorithm), task Least-common-multiple
- Task/Levenshtein-distance/Python/levenshtein-distance-5.py: problem_007 (algorithm), task Levenshtein-distance
- Task/Perfect-numbers/Haskell/perfect-numbers-1.hs: primelib (algorithm), task Perfect-numbers
- Task/Sorting-algorithms-Insertion-sort/Python/sorting-algorithms-insertion-sort-3.py: average_mode (algorithm), task Sorting-algorithms-Insertion-sort
- Task/Sorting-algorithms-Quicksort/Python/sorting-algorithms-quicksort-1.py: Sorting-algorithms-Cycle-sort (algorithm), task Sorting-algorithms-Quicksort

### Closed, measured, not built

- Class veto of the pipeline's wrong answers: overriding only an answer of a known, different class changes nothing on either set; overriding any answer of unknown class fixes 0 held-out answers and turns 15 correct specific TheAlgorithms answers (mergesort, tim_sort, jump_search, ...) into a class name. Not built.
- Haskell files that are not programs (GHCi transcripts, bare expressions, missing packages, deferred type errors) and Python scripts with no function: bad code under these criteria.

# Library-name fallback test (doc 04 section 18.1)

Order: algorithm answer (eval_ta.py), then a class relation (class_specs.pl), then a library name (library_names.pl), each only where the file is still UNKNOWN. Separate from the pipeline (eval_library.py).

| language | files | algorithm: correct / wrong / UNKNOWN | precision | recall | class: correct / wrong / UNKNOWN | precision | recall | answered by library name |
|---|---|---|---|---|---|---|---|---|
| C | 69 | 31 / 1 / 37 | 96.9% | 44.9% | 31 / 1 / 37 | 96.9% | 44.9% | 0 |
| Common-Lisp | 75 | 44 / 1 / 30 | 97.8% | 58.7% | 44 / 1 / 30 | 97.8% | 58.7% | 2 |
| Haskell | 144 | 29 / 2 / 113 | 93.5% | 20.1% | 31 / 2 / 111 | 93.9% | 21.5% | 0 |
| Python | 162 | 57 / 6 / 99 | 90.5% | 35.2% | 63 / 4 / 95 | 94.0% | 38.9% | 1 |
| all | 450 | 161 / 10 / 279 | 94.2% | 35.8% | 169 / 8 / 273 | 95.5% | 37.6% | 3 |

## Held-out files answered by a library name (3)

- Task/Factorial/Python/factorial-1.py: factorial via {'functions': {'<toplevel>': ['factorial', 'factorial']}, 'file': 'factorial'} (correct)
- Task/Greatest-common-divisor/Common-Lisp/greatest-common-divisor-1.lisp: gcd via {'functions': {'<toplevel>': ['cl_gcd', 'gcd']}, 'file': 'gcd'} (correct)
- Task/Least-common-multiple/Common-Lisp/least-common-multiple-1.lisp: lcm via {'functions': {'<toplevel>': ['cl_lcm', 'lcm']}, 'file': 'lcm'} (correct)

## Held-out files with a library answer that was not needed (already answered) (0)


## TheAlgorithms/Python files with a library call as a function's whole result (2)

- divide_and_conquer/closest_pair_of_points.py (label closest_pair_of_points): file answer None, functions {'column_based_sort': ['sorted', 'sorting']}
- sorts/natural_sort.py (label natural_sort): file answer sorting, functions {'natural_sort': ['sorted', 'sorting']}

## Notes

- False positives: none. All 3 held-out library answers are correct. On TheAlgorithms the one file answer
  (natural_sort -> sorting) is correct. closest_pair_of_points, whose sorted() helper is not the file's algorithm,
  gets no answer.
- The gain is small: 3 files, from 35.1 % to 35.8 % algorithm recall and from 36.9 % to 37.6 % class recall. In the
  held-out files most uses of these names are not a library call:
  - most `gcd`, `factorial`, `isPrime` and `sieve` are people's own functions;
  - `bisect` searches wrap the call in checks;
  - Haskell `product` and `foldl` are already lowered to loops.
- Kept separate: no pipeline file is changed. Tests: tests/test_library_names.py (8 positives in 4 languages, 7 close
  negatives).

# Class fallback test (doc 04 section 18): held-out Rosetta files

The algorithm answers of eval_ta.py are kept; an UNKNOWN file is answered by the class relations (prolog/class_specs.pl) when exactly one holds. Class level: the answer names what the task computes (a named algorithm counts as its class). Separate from the pipeline (eval_classes.py).

| language | files | algorithm: correct / wrong / UNKNOWN | precision | recall | class: correct / wrong / UNKNOWN | precision | recall | answered by class relation | new class (runs, no relation) |
|---|---|---|---|---|---|---|---|---|---|
| C | 69 | 31 / 1 / 37 | 96.9% | 44.9% | 31 / 1 / 37 | 96.9% | 44.9% | 0 | 5 |
| Common-Lisp | 75 | 42 / 1 / 32 | 97.7% | 56.0% | 42 / 1 / 32 | 97.7% | 56.0% | 0 | 4 |
| Haskell | 144 | 29 / 2 / 113 | 93.5% | 20.1% | 31 / 2 / 111 | 93.9% | 21.5% | 2 | 17 |
| Python | 162 | 56 / 6 / 100 | 90.3% | 34.6% | 62 / 4 / 96 | 93.9% | 38.3% | 4 | 27 |
| all | 450 | 158 / 10 / 282 | 94.0% | 35.1% | 166 / 8 / 276 | 95.4% | 36.9% | 6 | 53 |

## Wrong at the class level (8)

- Task/Factorial/C/factorial-2.c: problem_020 (algorithm), task Factorial
- Task/Factorial/Haskell/factorial-8.hs: problem_020 (algorithm), task Factorial
- Task/Factorial/Python/factorial-7.py: problem_020 (algorithm), task Factorial
- Task/Fibonacci-sequence/Common-Lisp/fibonacci-sequence-9.lisp: signum (algorithm), task Fibonacci-sequence
- Task/Least-common-multiple/Python/least-common-multiple-2.py: gcd (algorithm), task Least-common-multiple
- Task/Levenshtein-distance/Python/levenshtein-distance-5.py: problem_007 (algorithm), task Levenshtein-distance
- Task/Perfect-numbers/Haskell/perfect-numbers-1.hs: primelib (algorithm), task Perfect-numbers
- Task/Roman-numerals-Encode/Python/roman-numerals-encode-2.py: magicdiamondpattern (algorithm), task Roman-numerals-Encode

## Where the UNKNOWN files went (counted from class_fallback.json)

| outcome | files |
|---|---|
| algorithm answer (eval_ta.py, kept) | 168 |
| answered by one class relation | 6, all correct (gcd 1, sorting 5) |
| two relations held (selection sort: `minimum` and `sorting`), left UNKNOWN | 1 |
| ran, no relation held ("new class") | 53 |
| did not run on the battery | 222 (185 of them in a task that has a class relation) |

- The class relations made no false positive: all 8 wrong class-level answers come from wrong algorithm answers of
  eval_ta.py (for example problem_020 for a factorial), not from a relation.
- None of the 53 "new class" files is really a new class: every one is a known Rosetta task. They are misses of the
  relations, caused by the AP13 interpreter computing the program wrongly or only partly (prime2 uses `any(...)` over
  a generator; an analytic Fibonacci gives fib(0) = 1 through float rounding). The relation rejecting them is correct.
- The 222 files that did not run are the recall limit: library calls the interpreter does not model
  (`math.factorial(n)`, `itertools.accumulate`), top-level scripts with no function taking an input, and constructs
  that do not lower. More class relations cannot reach these. Only a wider interpreter (an AP13 subclass) can.
- So the idea is sound where a program runs (6/6 correct, 0 wrong). But on this set it lifts class recall only from
  35.1 % to 36.9 %. It is not ready to join the pipeline.

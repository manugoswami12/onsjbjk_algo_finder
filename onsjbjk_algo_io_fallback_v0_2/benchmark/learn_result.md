# Learning test: learn new algorithms from Python, recognise them in Lisp, C, Haskell. FAILED (stopped after 2 retries)

Design: docs/04_LEARNING_DESIGN.md. Key: benchmark/learn_truth.json (frozen before learning).
- 12 Rosetta tasks no rule knows (hanoi, josephus, ackermann, leap year, roman encode, run-length, caesar,
  levenshtein, lcs, n-queens, matrix multiplication, knapsack).
- Learned from their 56 Python files, with 120 Python files of other tasks as negatives.
- Tested on unseen files with as many seeded negatives: Common Lisp 26+26, C 23+23, Haskell 44+44.

| Run | Change | C prec / rec | Haskell prec / rec | Lisp prec / rec |
|---|---|---|---|---|
| 1 | logic-flow tokens, covering with anti-unification (33 rules) | 1/1 / 1/23 | 0/0 / 0/44 | 0/1 / 0/26 |
| retry 1 | negative-based rule reduction; links by base name (34 rules) | 2/4 / 2/23 | 3/6 / 3/44 | 3/8 / 3/26 |
| retry 2 | + input->output fallback (AP13 io_catalog of the Python training files) | 2/4 = 50% / 8.7% | 8/11 = 72.7% / 18.2% | 3/8 = 37.5% / 11.5% |

What worked:
- Learned rules transfer for algorithms whose logic is the same in every language: Hanoi (Lisp, C), Ackermann
  (Lisp, C), Caesar (Haskell).
- Every input->output answer was right (Haskell: leap year 2, roman encode 1, Hanoi 2).
- The mechanism itself is checked on own programs (tests/test_learning.py: learned from two Python Hanoi
  versions, recognised in unseen Lisp and C, fib and sum rejected).

Why it fails:
1. Few, very different Python examples per task (2-10). The logic shared by all of them is either long and
   operand-bound (run 1: does not transfer) or, after reduction to what separates it from the other Python
   tasks, too general in other languages (retry 1: ackermann r1 fires on Levenshtein and LCS).
2. Different idioms change the logic flow: Haskell equations and list comprehensions, C arrays with index
   loops, Lisp loop macros. Equal algorithms do not give equal token streams.
3. The behaviour fallback covers little: 20 discriminative training behaviours over 7 labels. Many functions
   print instead of returning, take strings or matrices, or have two arguments outside the battery, and the C
   front end gave no behaviour for a two-argument function.

Hard cases (known tasks, normal process fails), learned from the Python files of those tasks:
    fibonacci-sequence-6.lisp                    fibonacci_like   normal=- learned=['ackermann']
    fibonacci-sequence-9.lisp                    fibonacci_like   normal=- learned=-
    luhn-test-of-credit-card-numbers-1.lisp      luhn             normal=- learned=-

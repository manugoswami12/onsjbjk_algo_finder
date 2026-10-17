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

---

# Round 2: learned only from Python, applied to Python, Lisp, C and Haskell. Staged. FAILED at stage 3 (stopped after 2 retries)

**Method** (docs/04 section 7). One relation is run in both directions, the way `sum(2,X,10)` and `sum(X,5,20)` are.
- `pattern(S)//1` is the form every fallback rule has: the tokens of S in order, with gaps.
- With S known, it checks whether a stream holds S.
- With S unbound, it is called on all streams of a label to learn S.
- Called once more over S, it gives the most general sub-pattern that no negative holds.

**Key.** `benchmark/learn_staged_truth.json`, frozen and committed before learning (commit 1f4dbdd).
- Held out as unseen Python tests: about a third of each task's Python files, 15 positives. They come with 15 unseen Python negatives from 30 seeded other tasks.
- Added to these: the Lisp, C and Haskell test units of round 1.
- Positives and negatives are interleaved, and the stages are the first 3/15/55/101 units.
- Learned from the other 41 Python positives, the 120 Python negatives and the Fibonacci/Luhn Python files.

**Stage 3** (units: josephus-problem-1.lisp, hailstone-sequence-1.hs (negative), towers-of-hanoi-1.c):

| Run | Change (general only) | Precision | Recall | Result |
|---|---|---|---|---|
| 1 | `pattern//1` both ways: lockstep shared skeleton, covering (35 rules) | 0/0 | 0/2 | FAIL |
| retry 1 | tokenizer: each linked function spliced in once per stream (was: at every call, depth 4) | 0/0 | 0/2 | FAIL |
| retry 2 | learner: from each S, the most general sub-pattern of its logic tokens that no negative holds (`general/3`) | 1/1 = 100% | 1/2 = 50% | FAIL |

**After retry 2:**
- **towers-of-hanoi-1.c: ok.** It matched `learned_pattern(towers_of_hanoi, r1) --> pattern([call('$self'), op(sub), op(sub), output])`, learned from towers-of-hanoi-1.py.
- **josephus-problem-1.lisp: UNKNOWN.**
  - The rule learned from josephus-problem-2.py (`r = (r+k) % i` in a loop) stayed that file's whole 15-token stream. Every sub-pattern of its 6 logic tokens (`loop, call(range), op(add), op(mod), op(add), op(mod)`) is held by some Python negative.
  - The Lisp stream holds neither `call(range)` nor the second `op(mod)`. In Python that `op(mod)` is the string format `'Survivor: %d' % r`.
  - The input→output fallback gave no answer for this Lisp file.
- **hailstone-sequence-1.hs: ok(neg).**

**Problems seen** (for the next decision; not fixed, since the retries are used up):
- **Too specific, then too general.** The most specific rule (a whole file) does not transfer. The most general one is only as safe as the negatives allow: with 120 negatives, 4 logic tokens often suffice (for example, `lcs r1 = [op(or), op(not), op(not), op(or)]`).
- **Python spellings in the logic tokens.** `%` used for formatting reads as `op(mod)`, and `range` is a call. These are differences of the Python front end, not of the algorithm.
- **Some rules are library calls only** (`caesar r1 = [op(sub), call(translate), call(maketrans), op(add)]`). They cannot transfer to languages without those calls.
- **The streams kept their blow-up until retry 1**: sieve-of-eratosthenes-9.py gave 4,987 tokens. They now stay under 600.

**Regression.** The ECL logic tests and `tests/test_learning.py` (now including the relation in both directions) pass. Lisp staged test, stage 101, with the new tokenizer: precision 50/51 = 98.0%, recall 50/59 = 84.7%, PASS (unchanged).

---

# Round 3: a learned algorithm is a new branch of the tree, at the node its Python logic reaches. FAILED at stage 3 (stopped)

**Method** (docs/04 section 8).
- **Node.** Each Python training file walks the normal tree: AP13 family paths plus `families_v02.pl`, in one process, `prolog/tree_main.pl`. The deepest node it reaches is C.
- **Learning.** The new algorithm becomes a child F of C: `learned_branch(C, Label, Rule) --> pattern(S)` in `prolog/learned_tree.pl`. F's condition is the round-2 `pattern//1` relation, checked only against the other training files that also reach C.
  - At the root, the condition needs AP13's 4 logic tokens.
  - Under a node, it only has to separate the label from the other programs there, so it may be empty.
- **Applying.** The test file walks the same tree. The learned children are tried from the deepest reached node upward; then the input→output fallback; then UNKNOWN.

Same frozen key (`benchmark/learn_staged_truth.json`), learned from Python only (161 files). 37 branches were learned, for example:
- `josephus r3` under `numeric>recurrence>josephus_recurrence`: `[]` (nothing else reaches that node);
- `n_queens r2` under `search>backtracking`: `[]`;
- `levenshtein r1` under `sequence_query`: `[op(eq), call(min)]`;
- `towers_of_hanoi r1` under `numeric>recurrence>double_recursion` (files 1 and 3): an 18-token skeleton, mostly operands.

**Stage 3: precision 1/1 = 100%, recall 1/2 = 50%: FAIL.** Stopped, as instructed (stop below 80%).

| Unit | Expected | Node reached | Answer |
|---|---|---|---|
| josephus-problem-1.lisp | josephus | numeric>recurrence>josephus_recurrence | **ok**, `josephus r3` (round 2: UNKNOWN) |
| hailstone-sequence-1.hs | (negative) | root | ok(neg) |
| towers-of-hanoi-1.c | towers_of_hanoi | numeric>recurrence>double_recursion (correct node) | UNKNOWN |

**Why Hanoi in C failed.**
- The two Python Hanoi files were joined into one branch. Their shared skeleton lost what separates Hanoi from Fibonacci under `double_recursion` (`output`, no `op(add)`).
- What is left has only `op(sub), op(sub)` as logic, which Fibonacci's `fib(n-1) + fib(n-2)` also holds. So the condition could not be shortened, stayed an 18-token operand skeleton, and the C file does not hold it.
- Learned from towers-of-hanoi-1.py alone, the condition at that node would be `[output]`. The own-program test (two own Python Hanoi files) gives exactly that.

**Branching found inconsistent across languages** (tests/test_learning.py now fails on it; left failing, not skipped):
- The own Lisp Hanoi `(towers (1- n) from spare to) (format ...) (towers (1- n) spare to from)` reaches `search>backtracking`, while the same logic in Python and C reaches `numeric>recurrence>double_recursion`.
- Cause: ECL compiles the second, tail-position self-call as a jump to the function start (a loop). AP13's `idiom(backtracking)` then sees "a self-call inside a guarded loop", and `rec_class(double_recursion)` sees only one self-call.
- The token streams already undo this (the `tail_loop` fact of `ecl_norm.pl`); the tree does not.

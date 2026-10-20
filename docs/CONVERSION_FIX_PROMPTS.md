# Prompts: how each hard case was solved (doc 04 section 19)

One prompt per kind of fix, written so it can be run again for a new case. Every prompt follows the same method.

## The method (run this for every change)

> A held-out file is answered wrongly. First find where the code's logic is traced wrongly: dump its facts
> (`learn_facts.tree_facts`) and compare them with the facts of the TheAlgorithms file that does the same thing in
> another form. Fix the conversion as a rule of the language, never of an algorithm, in our own layer (a front-end
> subclass, a fact normalisation in `prolog/`), never in `polyglot_logic`. Then check it against all existing data,
> in a copy of the repository:
> 1. hand-check on about 5 programs: the broken one, the TheAlgorithms form it should equal, and near negatives;
>    dump the broken program's facts and confirm they now equal the TheAlgorithms form, not only its node;
> 2. the tree nodes of all 1346 TheAlgorithms and 450 held-out files, old against new: every change must be explained;
> 3. relearn (`eval_ta.py --learn`), re-index the file-rule fingerprints (`ta_distinct.py --index`, then regenerate
>    `prolog/ta_file_components.pl` only; never rewrite `ta_file_rules.pl`), run `--run` and `--heldout`;
> 4. learnt code must stay 1344/1344 with 0 differences and no new wrong answer may appear.
> A file that worked before and breaks is checked once: regenerate its generated parts; if it still breaks and the
> idea itself cannot fix it, drop the change.

## Cases solved

### Rule order in the tree (prolog/families_v02.pl)
> AP13's one-level fallback nodes ([numeric], [sequence_query], [sequence_transformation]) must hold only when no
> branch below applies. Find functions that reach both a deep v0.2 node and an unrelated fallback node; make
> deepest_families_v02/2 drop the one-level fallback when a v0.2 branch below the root holds. Check that only the
> stray fallback nodes disappear and no answer changes.

Result: 12 files lost a stray node; 0 answers changed.

### Stale rule placement (prolog/learned_ta.pl)
> A fresh run of unchanged code loses answers the committed results have. Compare each lost file's current tree node
> with the node its learned branch is placed at. If they differ, the branches were learned on an older tree: relearn
> with the current tree and rerun everything; never reuse old evidence.

Result: 11 lost answers back (dbscan, booths_algorithm, problem_074 ...); learnt 1344/1344 from fresh evidence.

### The tier decision in Prolog (prolog/decide.pl)
> Move the choice of the deciding tier from Python into Prolog: tiers as data (tier/2), every label of a tier
> collected (setof), no cut, no clause order. Replay the stored evidence of every file through the old and the new
> decision; they must agree on every file before the Python one is replaced.

Result: 1767 decisions, all equal.

### A return through the variable holding a recursive call (prolog/trace_returns.pl)
> `z = 1; if n > 1: z = n * f(n - 1); return z` is not traced as `return n * f(n - 1)` (AP13 propagates only
> single-definition variables). Trace two value-flow shapes by line order and guards: the last definition holding on
> every path; a default plus one guarded override (split into two guarded returns). Only values holding a recursive
> call; only when the variable is read nowhere but in the return; the call's facts move with its value.

Faults met and how: `black_height` lost its node (its variables are also tested: trace only a variable used only in
the return); three file rules stopped matching (their fingerprints were generated from the old facts: regenerate the
fingerprints, the rules unchanged). Result: factorial-7.py problem_020 -> Factorial; learnt 1344/1344.
Two later fixes, each re-checked against all data with no answer change: only reads AFTER the traced definition block
the tracing (the appends that build `lesser` read its earlier value); never substitute inside a recursive call's
arguments (`f(lesser)` was traced again into `f(f(lesser))`, eight times).

Lesson: "no answer changed" is not enough. In the hand check, dump the facts of the very file the change is for and
confirm they come out exactly in the TheAlgorithms form (`concat([f(lesser), equal, f(greater)])`); the nesting bug
passed two full checks because no answer depended on it.

### A Haskell recursion with no loop condition (haskell_logic.py base_case_conditions)
> `go acc 0 = acc; go acc n = go (acc * n) (n - 1)` lowers with no loop condition, so the accumulation rule (an update
> guarded only by the loop's continuation) cannot hold; the Python lowering derives the condition from every base
> case. Derive it the same way in the Haskell front end: the guard of a return without a self-call gives
> not(guard); a guard the self-call steps also carry is inherited context, not a base case.

Faults met: sieve-of-eratosthenes-16.hs's `adjust` changed node because AP13 nests a called local function under its
caller's loop (under/2) and both name an unnamed parameter `$arg0` (a separate lowering fix: unique names); no answer
changed. Result: factorial-8.hs problem_020 -> UNKNOWN (no longer wrong).

### Behaviour lowering: Lisp `finally`, C `x op= y` (lowering_v03.py, installed by crosslang_frontends)
> A program runs to the wrong outputs on the battery (fib(n) = 1 for n >= 2; factorial(n) = n). Dump its behaviour
> normal form (`io_trace.normal_form`) and find the statement lowered against the language's semantics: `finally`
> placed inside the loop body; `x *= y` lowered as `x = y` because the operator sits in a field the lowerer reads only
> for Python's kind. Fix the lowering method in our layer, then compare the normal forms of all files old against new:
> none of TheAlgorithms may change (the catalog depends on it), and every changed held-out file must use the construct.

Result: 28 normal forms change (C and Lisp only); fibonacci-sequence-9.lisp signum -> Fibonacci-sequence.

### An input check that guards the loop (prolog/families_v02.pl continuation_guard/4)
> A rule that requires an update to be unconditional fails because an early exit (`if (n < 0) return -1;`) puts its
> guard on every later statement. Treat a guard that EVERY loop around the update also carries as the nest's
> context, not a condition of the update; check sieves and other conditioned updates stay out.

### Logic matches contradicted by behaviour (eval_ta.TaLogic.consistent)
> An exact-logic (pattern) match names an unrelated algorithm. Drop the match only on a real contradiction:
> every function of the match computes varying outputs and the matched function computes none, or both compute
> outputs that differ on a common input. AP13's compare returning no verdict (too little evidence) is not one.

### Python tells about its own programs (pyast_facts.py, prolog/ast_concat.pl, prolog/slice_write.pl)
> Tree-sitter gives only the token: `a + b` cannot be told from a list join. Ask Python's own ast (static: the
> program is never run) which names hold lists (every assignment a list, annotated ones included, or appended to),
> which parameters are sliced and which functions return lists; add them as facts beside tree-sitter's. Rewrite an
> add with a list operand as concat, flattened (the same form `[*a, *b]` lowers to). Then the rules the old wrong
> reading had hidden must hold: a join of two recursive results is a partition sort only when the parts are split by
> a comparison (appended under one, or filtered by one), else Hanoi's moves are a sort. For an in-place rewrite
> `q[:] = E`: it is a write of q, and q the output, only in a function that returns nothing (one that returns
> already names its output).

Faults met and how (each one fix inside the idea, then all data again):
- 34 files failed to load: one predicate's facts were written apart (swipl's discontiguous warning is a failure).
  Write each predicate's facts together.
- The Lisp path never loads ast_concat.pl: declare `ac_joined/1` dynamic where it is read (families_v02.pl).
- problem_109 lost its file rule: Python did not see `singles: list[int] = ...` (annotated assignment), and the hand
  rule quoted the old wrong reading of `singles + doubles + triples + [0]`; read annotated assignments, and restate
  the rule's term in the corrected form (same rule, same uniqueness check).
- `[x] + lcs(...)` in the LCS built branch: the rule read the join only as `op(add, [list([_]), D])`; it accepts the
  corrected `concat([list([_]), D])` too (found by tests/test_uniform, not by the full check: run the tests too).
- `q[:] = E` everywhere broke rotate_matrix's reverse_column (it returns the matrix): limited to no-return functions.

Lesson: a corrected conversion changes the terms hand rules quote. Grep the hand rules and built branches for the
old form before the full run.

### A function that returns a function; a nested function; a helper (returns_function.py, behaviour_v04.py, interp_v04.pl, eval_ta.helper_functions)
> First tell whether a function returns a value or a function (every own return a lambda). A value: nothing changes.
> A function: lower it exactly as a new function, recursively: f(x) returning lambda y: E is f(x, y) returning E,
> and h(a)(b) is h(a, b). Then make what it computes evaluable, again as rules of the language: a nested function
> reading its enclosing function's variables takes them as parameters (lambda lifting; as a value it is a closure);
> a parameter passed to list()/zip() is a sequence; the library relations the interpreter lacks (n-ary zip/min/max,
> accumulate, reduce, a boolean as 0/1). Last, the decision: a function called by one that computes something else
> is that function's step, so its evidence (behaviour, built/hand branch, exact logic) does not name the file.

Method followed: each part built by hand on the two files first (scratch: the lifted normal form printed, the
interpreter called on kitten/sitting -> 3, the helper rule applied to the printed per-function evidence), then in a
copy of the code, hand-checked on the 13 held-out and 4 TheAlgorithms files with such functions, then all data.
Faults met: interp_v03's reduce never worked (foldl/6 with a state pair: write the fold as plain recursion); the
exact-logic tier is per file, so the helper rule needs the functions of each match (TaLogic.labels_matched by_match);
the facts lowering must be installed where the facts are made (learn_facts), not only with the front ends.

### The language's own parser checks tree-sitter's facts (haskell_ast_check.py, c_ast_check.py)
> Ask the language's own compiler for its AST (parsed only: GHC -ddump-parsed-ast; clang -ast-dump=json) and list the
> functions it defines. Compare with the functions and parameters tree-sitter's facts claim, over every file of the
> language; explain each difference before any rule (local functions, lambda lifting, escaped names are not faults).
> Drop only what the compiler says is not there; leave a file it cannot parse as it is.

## Tried and dropped (do not repeat)

- `q[:] = E` as a write of q in every function (before Python's facts): insertion-sort-3 became Cycle-sort and two
  learnt files were lost. Solved later, limited to functions that return nothing (above).
- Library files (roots computing different things) naming nothing: volume.py, rotate_bits.py and seven other
  learnt files lost or wrong; a file of several functions of one topic cannot be told from a library.
- Uncurrying `return lambda` (hand-tested only): the behaviour becomes right for lcm-2, but the hand-built gcd branch
  at its helper's node decides first; levenshtein-5's functional body (reduce, scanl, functions as values) still
  cannot be evaluated.

- `+` on lists as concatenation without types (prolog/list_concat.pl, removed): every `+` of a recursive result
  became a join, and AP13's partition idiom takes any join of two recursive results as a partition sort; Hanoi's
  moves and TheAlgorithms' huffman became Quicksort. Solved later with Python's facts and the partition test (above).

- Naming a match by the matched function's algorithm, in Python rules added case by case (mixed answers): removed 9
  wrong answers but lost 19 learnt answers and made 2 wrong. Rules in Python patched per case are hard coding.
- Branches written from failing held-out files (partition through variables, `seq[:] = ...`): test-set rules; removed.
- Placing a file's label only at its roots' nodes: moves 248 learnt files (136 to no node), because TheAlgorithms
  often writes the algorithm in a helper (`all_combinations.py`'s root only calls `create_all_state`).
- The perfect-number trace (doc 04 section 19.9): a generator argument as one comprehension plus an input-check rule
  fixed perfect-numbers-1.hs by hand, but lost is_power_of_two.py (happy_number then runs, still converted wrongly)
  and made primality-by-trial-division-1/2 wrong (`if n <= 3: return True` is part of is_prime, not an input check).
  Fix first: int() of a character in the interpreter; an input check told from a base case.

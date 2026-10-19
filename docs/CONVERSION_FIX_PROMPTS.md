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

## Tried and dropped (do not repeat)

- `q[:] = E` as a write of q: insertion-sort-3 became Cycle-sort and two learnt files were lost.
- Library files (roots computing different things) naming nothing: volume.py, rotate_bits.py and seven other
  learnt files lost or wrong; a file of several functions of one topic cannot be told from a library.
- Uncurrying `return lambda` (hand-tested only): the behaviour becomes right for lcm-2, but the hand-built gcd branch
  at its helper's node decides first; levenshtein-5's functional body (reduce, scanl, functions as values) still
  cannot be evaluated.

- `+` on lists as concatenation (prolog/list_concat.pl, removed): the conversion was right, but AP13's partition idiom
  takes any join of two recursive results as a partition sort; Hanoi's moves and TheAlgorithms' huffman became
  Quicksort. Fix the partition rule (parts filtered by a pivot comparison) first, then retry this.

- Naming a match by the matched function's algorithm, in Python rules added case by case (mixed answers): removed 9
  wrong answers but lost 19 learnt answers and made 2 wrong. Rules in Python patched per case are hard coding.
- Branches written from failing held-out files (partition through variables, `seq[:] = ...`): test-set rules; removed.
- Placing a file's label only at its roots' nodes: moves 248 learnt files (136 to no node), because TheAlgorithms
  often writes the algorithm in a helper (`all_combinations.py`'s root only calls `create_all_state`).

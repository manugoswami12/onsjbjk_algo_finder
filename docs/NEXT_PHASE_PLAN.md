# Next phase plan: implementing the handover

This is the full working plan for the next phase. Read it together with `docs/HANDOVER.md`: its section 4 (the
working rules) and section 5 (the method) apply to every step here. The plan is written so that a new session, with
no memory of earlier ones, can pick it up at any step: each step says where in the code it works, shows a worked
example with hand-computed expected values, names its tests and its acceptance check, and lists its risks. Keep the
progress log at the end up to date after every step.

---

## 0. How to use this plan

**Owner's decisions (at close):**
- Scope: the whole plan, phases 0 to 3, in order, stopping wherever a step fails the method.
- Dead code is **archived** in `older_code/archive/`, never deleted.
- This plan lives in the repository and is updated as work goes on.

**Resuming after a reset:**
1. Read `docs/HANDOVER.md` sections 1 to 5, then this file's progress log (section 8).
2. `git fetch origin main && git checkout -B BRANCH origin/main` (a merged pull request is finished; new work is a new
   pull request).
3. `python tools_manual/check/verify_data.py` must end with `all match the tested data`.
4. Continue at the first step not marked done.

**The method, short form (handover section 5):**
1. Work in a copy: `mkdir COPY && tar cf - --exclude=.git . | (cd COPY && tar xf -)`. Never `--exclude=benchmark`
   (it also drops `polyglot_logic/benchmark` and the runs crash silently).
2. Hand-test on small own programs with hand-computed results, a near negative, and the real file the change is for.
   Add them to `tests/`.
3. `tools_manual/check/fullcheck.sh COPY NAME OUT_DIR` (about an hour, one at a time). Accept only if: learnt answers
   0 differences; no correct held-out answer lost; no new wrong answer (pipeline and fallback); tree-node changes
   explained; no traceback.
4. A failure gets one fix attempt; if it does not work, drop the idea and record it with its reasoning.
5. If kept: all `tests/`, rebuild the report (README section 4 steps b to d), update the docs (section 6 of this
   plan), commit, push.

**Writing every problem down (owner's request):** each problem met becomes a prompt in
`docs/CONVERSION_FIX_PROMPTS.md`, with its solution or its reason for being dropped, in the existing format.

---

## 1. Phase 0: baseline (about half a day)

### 0.1 Check the inputs
- `python tools_manual/check/verify_data.py` -> `2231 files: all match the tested data`.
- Tool versions as in handover section 8: `python3 --version` (3.13.16), `swipl --version` (9.0.4),
  `ghc --numeric-version` (9.4.7), `ecl --version` (21.2.1), `clang --version` (18.1.3). A different version is
  allowed, but then 0.2 decides whether results still match.

### 0.2 Run the full check on unchanged code
The script `tools_manual/check/fullcheck.sh` was syntax-checked at close but never run end to end from its place in
the repository. Run it on an unchanged copy:

```
mkdir -p ~/work/base && tar cf - --exclude=.git . | (cd ~/work/base && tar xf -)
tools_manual/check/fullcheck.sh ~/work/base base ~/work/out
```

Expected: `learnt differ 0`, `fingerprints differ 0`, `new code right/wrong: now (173, 0)  with the change (173, 0)`,
tree nodes `0 changed`, no `TRACEBACK` line. It also writes `~/work/out/n_base.json`, the node baseline every later
check compares against. If anything differs, fix the script before any other step.

### 0.3 A fast check for refactors: `tools_manual/check/nf_snapshot.py`
A pure refactor must not change anything the pipeline computes. The full check proves that in an hour; a snapshot
proves it in minutes. The new script writes, for all 1796 data files (1346 TheAlgorithms + 450 held-out):
- the tree facts: `learn_facts.tree_facts(path)` (text);
- the behaviour normal form: `io_trace.normal_form(path)` (rendered with `to_prolog.render`);
- the battery runs: `io_trace.run_functions(path)` (inputs and results per function);
- any exception, as text.

```
python tools_manual/check/nf_snapshot.py OUT.json            # in a copy
python tools_manual/check/nf_snapshot.py --compare A.json B.json
```

Compare prints the files whose facts, normal form or runs differ, with the first differing line. Acceptance for a
refactor: `0 files differ`. Add `tests/test_nf_snapshot.py`: two snapshots of the same three small files are equal;
changing one file's source makes compare report it.

### 0.4 Record the baseline
Keep `~/work/out/n_base.json` and a snapshot `~/work/out/nf_base.json` for phase 1. Write the date and the commit
in the progress log.

---

## 2. Phase 1: clean-up (handover 10.1), results must not move

The order is chosen so that every step can be checked, and later steps work on a cleaner base. Step 1.4 depends on
phase-2 step 2.1 and is done right after it.

### 1.1 One front end per language (pure refactor, about 3 days)

**What is there now.** `crosslang_frontends.install()` patches AP13's classes method by method, in this order:

| Order | Module | What it patches | Rules |
|---|---|---|---|
| 1 | `crosslang_frontends` | `io_trace.normal_form` | Haskell through `haskell_core_pnf`; C through the cpp-expanded text; output formatting stripped |
| 2 | `lowering_v03` | `LispPNF.f_loop`, `PNFLowerer.assign_term` | Lisp loop `finally`; C `x op= y` |
| 3 | `returns_function` | `ImperativeLowerer` and `PNFLowerer`: `run`, `function`, `params`, `expr` | a function returning a lambda is a function of more parameters (19.8) |
| 4 | `lowering_v05` | `LispPNF` (`defun`, `run`, `place`, `f_case`, `f_subseq`, `f_last`, `f_map`), `PNFLowerer` (`st`, `expr`, `function`) | the 19.17 rules for C, Python, Lisp |
| 5 | `generators` | `PNFLowerer.function`, `st` | a generator is the list it yields (19.14) |
| 6 | `behaviour_v04` | `io_trace.run_functions`, `io_trace._uses` | lambda lifting, constants, the v0.4 runner, sequence kinds |

The facts side: `learn_facts` wraps `env_run.run` (single-threaded GC, 19.16) and installs `returns_function` on
`imperative_logic.ImperativeLowerer`.

Each module patches what the one before patched, so the meaning of `PNFLowerer.expr` depends on the import order,
and one rule can hide another: in 19.17 the lambda rule silently overrode the returns-function rule until a test
caught it.

**Target layout.**

```
frontends/
  __init__.py      install(): the single patch point (see below); nothing else patches AP13
  python.py        class PythonPNF(PNFLowerer): returns-function, lambda, generators, constants, unpacking
  c.py             class CPNF(PNFLowerer): cpp text, effects, arrays, casts, literals, / and %, strlen, x op= y
  lisp.py          class LispPNFv05(LispPNF): loop finally, case, subseq, &optional, last, map
  haskell.py       haskell_core_pnf moved here, unchanged
  runner.py        behaviour_v04 moved here: lifting, constants, kinds, run_functions
  facts.py         the imperative_logic additions (returns-function on the facts side)
```

The single patch point: `io_trace.normal_form` is replaced by one function that picks the class by language
(`PythonPNF`, `CPNF`, `LispPNFv05`, Haskell Core) and calls `run()`; `io_trace.run_functions` and `io_trace._uses`
are replaced by `frontends.runner`. Rules become ordinary methods with `super()` calls, so the order is the class
order, visible in one file.

**Example, before and after** (the lambda rule):

```python
# before (lowering_v05.install): a function replaces PNFLowerer.expr on the class, and must remember
# to leave returned lambdas to returns_function, which patched expr before it
def expr(self, node):
    if self.lang == 'python' and node.type == 'lambda' and (node.start_byte, node.end_byte) not in self.rf_bodies:
        ...
    return expr0(self, node)
cls.expr = expr

# after (frontends/python.py): an ordinary method; the returns-function rule is a method of the same class
class PythonPNF(PNFLowerer):
    def expr(self, node):
        if node.type == 'lambda' and not self.is_returned_lambda(node):
            return ('lambda', self.lambda_params(node), self.expr(node.child_by_field_name('body')))
        return super().expr(node)
```

**Steps.**
1. Create `frontends/` and move one language at a time (Lisp first: it is the smallest), keeping the old modules as
   thin shims that import from `frontends/` (so `crosslang_frontends.install()`, `lowering_v05.install()`, tests and
   docs keep working during the move).
2. After each language: `nf_snapshot` against `nf_base.json` -> 0 files differ; all `tests/`.
3. When all four are moved: one full check -> 0 differences in answers **and** evidence
   (`benchmark/ta_answers.json` and `ta_heldout.json` byte-identical, since the GC fix makes runs repeatable).
4. The shims are removed in 1.3.

**Risks.** A rule that depended on patch order behaves differently as a method (the 19.17 lambda/returns-function case
is the known one): the snapshot shows it on the first run. AP13 code that constructs `PNFLowerer` directly
(search `PNFLowerer(` in `polyglot_logic/tools`) must go through the new single point; list every construction site
before starting.

### 1.2 Inference limits instead of wall-clock limits (about 2 days)

**What is there now.** Every SWI-Prolog call goes through `polyglot_logic/tools/env_run.swipl` with a 120-second
wall-clock limit (the AP13 scan), `learn_apply` uses 3600 s, `logic_canon` 120 s, `haskell_core_pnf` 90 s (GHC), ECL
120 s. A wall-clock limit depends on the machine and its load: `project_euler/problem_111/sol1.py`'s canonical scan
hits 120 s every time today, and a second heavy job on the same machine could push another file over. The behaviour
runs already use an inference limit (2,000,000 per job, `run_main.pl`).

**Step A, measure** (scratch only, nothing committed). Extend the `env_run.run` wrapper in `learn_facts.py` for one
full run so every goal is wrapped as:

```prolog
statistics(inferences, I0), Goal, statistics(inferences, I1), I is I1 - I0,
format(user_error, '~w~n', [inferences(GoalName, I)])
```

(stderr output makes `env_run.swipl` treat the call as failed, so for the measurement write to a log file instead of
stderr.) From the log, for each goal kind (`scan_main`, `learn_all_main`, `tree_main`, `decide_main`, ...): the
largest count among calls that succeed today, and the counts of the calls that time out.

**Step B, the limit.** In the same wrapper, the goal becomes

```prolog
call_with_inference_limit(Goal, N, R),
( R == inference_limit_exceeded -> format(user_error, 'inference limit ~w~n', [N]) ; true )
```

with N per goal kind, about 4x the largest successful count from step A. A message on stderr already makes
`env_run.swipl` raise `ToolError`, which the callers treat exactly as they treat a timeout today, so nothing else
changes. The wall-clock limit stays only as a safety net, raised to 30 minutes. GHC and ECL are external compilers,
not Prolog: they keep a wall-clock limit, raised from 90/120 s to 600 s (they never came near it).

**Example.** problem_111's canonical scan: today it is cut at 120 s, so the canonical view has no evidence for it.
With an inference limit it either finishes (new evidence) or stops at the same count on every machine.

**Acceptance.** Full check: no lost success, no new wrong answer. Evidence may change only for calls that hit the
wall clock before (list them from step A). Then run the full check a second time on another load (for example while
another heavy process runs): identical results prove the load-independence.

### 1.3 Archive dead code (about 1 day)

**Not reached from any entry point or test** (measured at close): `corpus_roots` (tools_manual), `ecl_witness`,
`eval_crosslang`, `eval_crosslang_ext`, `eval_ecl`, `eval_ecl_staged`, `eval_heldout`, `eval_learn`, `eval_library`,
`popper_fallback`, `ta_prompts`. (`cmp_nodes` is used by fullcheck.sh: keep.)

Decision per file:
- **Keep in place** what a current document tells a reader to run: `eval_learn.py` (the staged run in
  `docs/HAND_RULE_PROMPTS.md`), `ta_prompts.py` (generates `docs/RULE_PROMPTS.md`).
- **Archive** the rest into `older_code/archive/v02_tools/`, with `older_code/archive/README.md`: one line per file
  saying what it did, which result file it produced (e.g. `eval_ecl.py` -> `benchmark/crosslang_ecl_result.md`), and
  why it is archived ("a v0.2 experiment, not part of the pipeline"). Update the documents that cite them
  (`docs/03_V02_ECL_LOGIC_DESIGN.md`, `docs/README_v02_details.md`) to the new paths.
- Remove the shims of 1.1 (`crosslang_frontends` becomes a one-line alias of `frontends.install`, or is archived
  once every caller uses `frontends`).

**older_code/.** Keep in place exactly what live code loads:
`older_code/algo_reference_corpus/ap12/prolog/route_extended.pl` (env_run, `prolog/ecl_main.pl`),
`older_code/algo_reference_corpus/` (knowledge_store), `older_code/semgrep_prolog_poc/tools/` (fact_io), and the
example files `polyglot_logic/tests/test_ap13.py` reads (`onsjbjk_algo_io_fallback_poc_v0_1/examples`,
`semgrep_prolog_poc/examples/candidate.py`). Before moving anything, list every path under `older_code/` that any
`.py` or `.pl` outside `older_code/` opens (grep `older_code` and each subfolder name); move only what is on no list.
`AP13_polyglot_logic_handover.zip` moves to the archive.

**Acceptance.** `nf_snapshot` 0 differences; all `tests/` **and** `python -m unittest discover polyglot_logic/tests`;
`./analyze.sh` on one file per language; full check.

### 1.4 Merge the two behaviour runners (right after 2.1)

**What is there now.** The pipeline uses `behaviour_v04` (19.17 rules, no generator-argument rule). The class
fallback (`tools_manual/decide_new_or_known.py --v03`, `ta_classes.runs(v03=True)`, and `analyze.py`'s fallback)
uses `pnf_v03` (`PNFv03`, `prolog/run_main_v03.pl`, which does not load `interp_v04.pl`), which still has the
generator-argument rule. At close, rebuilding the left-out list with the pipeline's runner lost two fallback answers
(primality-by-trial-division-1.py and -2.py), which need the generator rule. After 2.1 brings the generator rule back
to the pipeline, the merge loses nothing.

**Steps.** `pnf_v03.run_functions` and `pnf_v03.normal_form` delegate to `frontends.runner`; `run_main_v03.pl`
loads `interp_v04.pl`; the `--v03` flag stays accepted (no-op) for the documented commands; rebuild
`held_decided.json`, `decision_fallback.json` and the report (README section 4 b to d). Acceptance: no fallback answer
lost, 0 wrong, the left-out list now agrees with what the pipeline can run. Update handover 7 ("two runners") as
solved.

---

## 3. Phase 2: upgrades (handover sections 6 and 7)

### 2.1 Characters as their own values (about 1 week; unblocks the most)

**The problem** (handover 6.1). A string is a list of character codes, so `'7'` is 55 and `int(c)` on the character
`'7'` returns 55, not 7. Any code that iterates a string and converts characters runs with wrong values.

**Representation.** Each language keeps its own semantics:

| Language | A character is | A string is | Reason |
|---|---|---|---|
| Python | `char(C)`, which behaves as a 1-character string | a list of `char(C)` | in Python `s[i]` is a string of length 1 |
| Haskell | `char(C)` | a list of `char(C)` (`String = [Char]`) | `Char` is not `Int`; `ord`/`chr` convert |
| Common Lisp | `char(C)` (`#\a`) | a list of `char(C)` | characters are their own type |
| C | the integer code | an array of integer codes | in C a `char` is an integer: `'a' + 1 == 98` |

**Operations to update** (in `prolog/interp_v04.pl`, before the older interpreters' clauses), with the expected value
of each:

| Operation | Example | Expected |
|---|---|---|
| literal | `'abc'` | `[char(97), char(98), char(99)]` |
| index | `'abc'[1]` | `char(98)` |
| iterate | `for c in 'ab'` | `c = char(97)`, then `char(98)` |
| `int` | `int('7')`, `int(char(55))`, `int('42')` | `7`, `7`, `42` |
| `ord` / `chr` | `ord('a')`, `chr(98)` | `97`, `char(98)` |
| `str` | `str(42)` | `[char(52), char(50)]` |
| compare | `'a' < 'b'`, `char(97) == 'a'` | `true`, `true` (a char equals the 1-char string) |
| concatenate | `'ab' + 'c'` | `[char(97), char(98), char(99)]` |
| join | `''.join(['a', 'b'])` | `'ab'` |
| methods | `'aB3'.upper()`, `'a'.isalpha()`, `'7'.zfill(3)` | `'AB3'`, `true`, `'007'` |
| Haskell | `digitToInt 'f'`, `show 42` | `15`, `"42"` |
| C | `'a' + 1`, `strlen("abc")` | `98`, `3` (unchanged: integers) |

The battery's existing integer and list inputs stay exactly as they are, so functions that do not use strings run as
before: that is what keeps the learnt answers stable.

**Hand tests** (`tests/test_characters.py`), each value worked out by hand:
- `is_happy(7)` -> `true` (7 -> 49 -> 97 -> 130 -> 10 -> 1); `is_happy(4)` -> `false` (enters the 4 -> 16 -> 37 -> 58
  -> 89 -> 145 -> 42 -> 20 -> 4 cycle).
- `digit_sum(1234)` written as `sum(int(c) for c in str(n))` -> `10` (needs the generator rule, re-added below).
- A Caesar shift of `'abc'` by 3 -> `'def'`; a palindrome check of `'racecar'` -> `true`, of `'ab'` -> `false`.
- Haskell `sum (map digitToInt (show 1234))` -> `10`.

**Then re-add the generator-argument rule** (handover appendix A.1) and check, against the real files, that they now
behave as Python does: TheAlgorithms `happy_number.py` (`is_happy_number(7)` true), `is_power_of_two.py` keeps its
answer, `perfect_number.py`, `perfect-numbers-1.hs`, `perfect-numbers-3.py` keep theirs, primality-1/2.py name
nothing wrong.

**Then string inputs in the battery.** A parameter gets the kind `str` when the function uses it as text: a string
method on it (`s.upper()`, `s.split()`, `s.isalpha()`), comparison of its elements with a character literal, or
passing it to `ord`, `int`, `''.join`. The string battery, fixed and deterministic like the others:
`'', 'a', 'ab', 'abc', 'aba', 'racecar', 'Hello World', 'The quick brown fox', 'AbC123', '7', '42', 'zzz'`, and
for `(str, int)`: those strings with `0, 1, 3, 13, 25`. Expected newly evaluated files (from the handover's upgrade
list): Python Caesar ciphers, palindromes, run-length encoding, Roman numerals; Haskell `digitToInt`/`show` code;
Lisp string code.

**Acceptance.** The method; the fingerprints file changes (new evidence), learnt answers must not. Then do 1.4.

**Risks.** A wrong representation choice for one operation shows as a lost learnt answer: the full check finds it;
the fix is in that operation only. If more than one fix is needed, drop and record (the method).

### 2.2 A helper does not name a file whose main functions cannot run (about 3 days)

**The problem** (handover 6.2, 6.3, 10.2). When a file's main functions cannot run, a small helper that can run may
name the whole file: PostgreSQL's `binaryheap.c` was named `minimum_spanning_tree_prims` from its index formulas
`2i+1`, `2i+2`, `(i-1)/2`; `fibonacci-sequence-16.hs` was named `round_robin` from its matrix helpers.

**Measure first** (scratch). For every learnt and held-out answer today, record which functions' evidence decided it,
and whether those functions are roots or helpers of roots that cannot run. Count the learnt answers that a rule
"evidence only from helpers of unrunnable roots does not name the file" would remove. The earlier, broader idea
(only roots name a file) moved 248 learnt files, so this count decides the rule's form before any code.

**The rule** (in `eval_ta.helper_functions`, which already handles helpers of roots that *do* run): a function F is a
helper when a root of the file calls it, directly or through others; if every root that calls F has no behaviour
(it does not run), F's evidence is held back. The file is then named only if a root's own evidence or traced logic
names it; otherwise the answer is UNKNOWN, with the part reported:

```
binaryheap.c (C)
  algorithm: not named
  contains:  binary-heap index arithmetic (left_offset, right_offset, parent_offset), as in minimum_spanning_tree_prims
```

**Then re-add the two dropped rules:** appendix A.2 (C declarations without a value, about 16 C files) and A.3 (the
Core reader's operator tokens, 8 Haskell files). Check the three files that went wrong at close:
`sorting-algorithms-pancake-sort-2.c` (only `do_flip`: now UNKNOWN or "contains a reversal"), `fibonacci-sequence-16.hs`
(matrix helpers: now UNKNOWN), `fibonacci-sequence-2.c` (see below).

**A decision for the owner at that point:** `fibonacci-sequence-2.c`'s `fibb` is a root, it runs, and its sequence
is the Fibonacci recurrence with a shifted start, which equals TheAlgorithms' `climbing_stairs`. The helper rule does
not change it. Options to put to the owner: answer the family ("a Fibonacci-recurrence sequence") through the
existing family answer of `eval_decision.py`; or keep A.2 out for that file's shape. Do not add `climbing_stairs` to
the Fibonacci label group by hand (a test-set rule).

### 2.3 C structs and pointers (about 2 weeks; what real code needs most)

**The problem** (handover 7 item 5, 10.2). Real C passes `struct node *` and `heap *`; GTK's red-black tree did not
run a single one of its 40 functions.

**Representation** (in our layer: `frontends/c.py` and `interp_v04.pl`):
- a struct value is a record in the heap: `rec([key-V1, left-V2, ...])`, created by a declaration or by
  `malloc(sizeof(struct node))`;
- `a.key` and `p->key` read and write the field (`p->key` = the field of the record `p` points to);
- a pointer is `ptr(Ref, Offset)`: `&x` for an array element or record, `p + i` adds to the offset, `*p` and `p[i]`
  read the cell, `p == NULL` / `!p` test for `null`;
- `NULL` is `null`; `free(p)` does nothing (as now).
The battery does not invent struct inputs: a root that takes a struct pointer stays unrunnable unless the file builds
the structure itself. That is honest: the structure's meaning is not known from outside.

**Hand tests** (expected values by hand):

```c
struct node { int key; int left; };
int f(int n) { struct node a; a.key = n; a.left = 2 * n; return a.key + a.left; }        /* f(4) = 12 */

int g(int n) { int b[3] = {1, 2, 3}; int *p = b; p = p + 1; *p = n; return b[1] + *(p + 1); }  /* g(4) = 7 */

struct item { int v; struct item *next; };
int sum3(int n) { struct item c = {n, 0}; struct item b = {2, &c}; struct item a = {1, &b};
                  int s = 0; for (struct item *p = &a; p; p = p->next) s += p->v; return s; }  /* sum3(4) = 7 */
```

**Outside check, not scored:** the PostgreSQL `binaryheap.c` and GTK `gtkrbtree.c` of handover 10.2 (download them
again into a scratch folder). Expected: their internal functions (`sift_down`, `gtk_rb_node_rotate_left`, ...) now
run when called from code that builds a heap or a tree; the files themselves stay UNKNOWN unless a root builds its own
structure, and must never be named wrongly.

**Acceptance.** The method. Expected newly evaluated held-out C files: the pointer cases of handover section 7
(about 9).

### 2.4 Haskell: laziness, Maybe/Ordering/arrays, monads (about 2 weeks)

**Infinite lists** (about 16 files). A top-level list with no parameters that is infinite (`fibs`, `primes`,
`factorials`) becomes the function `n -> xs !! n`, evaluated lazily only as far as index n (the battery's largest n
is 496, so the work stays bounded; a per-job inference limit still applies).

```haskell
fibs = 0 : 1 : zipWith (+) fibs (tail fibs)     -- as a function of n: fibs !! 10 = 55, fibs !! 0 = 0
factorials = scanl (*) 1 [1..]                   -- factorials !! 5 = 120
```

Then it is compared with TheAlgorithms' `fibonacci(n)` and `factorial(n)` by the existing behaviour tiers (with the
existing shifted-sequence comparison for 0- or 1-based starts). Needs: `[1..]`, `iterate`, `cycle`, `enumFromThen`,
`zipWith`, `tail` on lazy lists; implemented as a lazy-list term in the Core lowering with forcing in the interpreter.

**Maybe, Ordering, arrays** (about 6 files): `Just x`/`Nothing` as `just(X)`/`nothing`, `maybe d f m`; `LT`/`EQ`/`GT`
as atoms, `compare`, `comparing`, `maximumBy`, `minimumBy`; `Data.Array` (`listArray`, `!`, `bounds`, `//`) as a list
with its lower bound.

```haskell
safeDiv a b = if b == 0 then Nothing else Just (a `div` b)
f n = maybe 0 id (safeDiv 100 n)                 -- f 0 = 0, f 7 = 14
g xs = fst (maximumBy (comparing snd) (zip [0..] xs))   -- g [3,9,4] = 1
```

**Monads** (about 9 files): `IO` as statements with `print`/`putStrLn` as effects (no output value);
`ST` with `newSTRef`/`readSTRef`/`writeSTRef` and `STUArray` (`newArray`, `readArray`, `writeArray`) as local heap
cells; `runST` returns the final value; `foldM`, `mapM_`, `forM_`, `when` as loops and conditionals.

```haskell
sumST :: Int -> Int
sumST n = runST $ do { r <- newSTRef 0; forM_ [1..n] (\i -> modifySTRef r (+i)); readSTRef r }  -- sumST 4 = 10
```

### 2.5 Common Lisp (about 1 week)
`loop` with `with`, `and`, `nconc`, `collect into`; `&key` parameters (like `&optional`, by name); `complement`;
`mapc`; `multiple-value-list`, `multiple-value-bind`, `values`.

```lisp
(defun tri (n) (loop with s = 0 for i from 1 to n do (incf s i) finally (return s)))   ; tri 4 = 10
(defun dup (n) (loop for i from 1 to n nconc (list i i)))                              ; dup 2 = (1 1 2 2)
(defun scale (x &key (k 2)) (* x k))                                                   ; (scale 5) = 10
```

### 2.6 Python libraries and programs with no input (about 1 week)
- `itertools.cycle` (only where it is consumed finitely: by `zip` with a finite list, or `islice`), `groupby`,
  `heapq.merge`; `complex` and numpy stay out (numbers and arrays of another kind).

```python
from itertools import groupby
def rle(s): return [(k, len(list(g))) for k, g in groupby(s)]   # rle('aaabcc') = [('a',3),('b',1),('c',2)]
```

- **No input.** A generator with no parameters (`def fib(): a, b = 0, 1; while True: yield a; a, b = b, a + b`) or a
  top-level script has no battery. Convention: take its first k values (k = 20) and compare that sequence with the
  outputs of TheAlgorithms' one-integer functions on `0..k-1` (with the shifted-sequence comparison). Example: the
  generator above gives `0, 1, 1, 2, 3, 5, 8, 13, ...`, equal to `fibonacci(0..19)`. A script that prints values is
  read through its printed sequence the same way.

### 2.7 Battery shapes (about 3 days)
- Tuple parameters: Haskell `f (n, (a, b))` gets tuple inputs built from the integer battery.
- A list plus its length passed separately, by use, not by name: an integer parameter used as a loop bound over
  indexes of a list parameter (`for (i = 0; i < count; i++) a[i]`) is that list's length (today only names like
  `n`, `len`, `size` are recognised).
- Inputs a program legitimately rejects (base 0 for a digit sum): an input where both the file and the TheAlgorithms
  reference raise counts as agreement, not as a failed run.

### 2.8 The matcher's order dependence (about 3 days, investigate first)
Handover section 7: in the order fixed by 19.16, `segment_tree.py` does not match its own learned pattern.
`polyglot_logic/prolog/leaf.pl` searches with `once(holds(R, N))`, which backtracks over all bindings, so the order
dependence must come from a relation that commits early (canon.pl's tabled `under/2`, `reaches/2`, or a `once/1`
inside a relation such as `raw_exchange`). Steps: reproduce on `segment_tree.py` against its own pattern; find the
relation whose answer order matters (`trace/1` on the relations of that pattern); then, in our layer (polyglot is not
edited), either load an override of that relation that enumerates every answer, or rerun a scan that finds no match
with the references in reverse order and keep a match only if found consistently. Acceptance: the method, plus
`segment_tree.py` matches itself.

---

## 4. Phase 3: egg, the first step (about 1 to 2 weeks)

Handover 10.3 explains the idea: our pipeline knows what code *is*; an e-graph searches what it *could be* and
extracts the cheapest equivalent, the modern Karnaugh map for code.

### 3.1 The Rust tool: `tools_manual/egg/`
- A Cargo crate pinned to one exact egg version (`egg = "=X.Y.Z"`: 0.9.5 was the current release at close; check
  crates.io and pin whatever exact version is current), vendored with `cargo vendor` into
  `vendor/egg/` with checksums, so it is frozen like tree-sitter (handover section 8). Rust is installed in the
  session container (`cargo`, `rustc`).
- Protocol: JSON on stdin, JSON on stdout.

```json
{"terms": {"left_parent": "(/ (- (+ (* 2 i) 1) 1) 2)"},
 "rules": [["sub-add", "(- (+ ?x ?y) ?y)", "?x"], ["div-mul", "(/ (* 2 ?x) 2)", "?x"]],
 "costs": {"gcd-sub": 100, "gcd-binary": 20, "gcd-euclid": 10},
 "limits": {"nodes": 10000, "iterations": 30, "seconds": 5}}
```

```json
{"left_parent": {"best": "i", "proved_equal": true, "stop": "saturated"}}
```

- Language: `SymbolLang` (any symbol with children) for the first step; a cost function that adds 1 per node and
  the given weight per algorithm symbol.

### 3.2 The exporter: `egg_export.py`
Only pure functions in the first step: no stores, no loops (until an SSA step exists). Haskell's Core functions are
pure already; Python and C functions qualify when their normal form has only returns, conditionals and calls.

| Normal form | S-expression |
|---|---|
| `('op', 'add', [a, b])` | `(+ a b)` |
| `('op', 'div', [a, b])` | `(div a b)` (Python floor) or `(cdiv a b)` (C truncation): different symbols |
| `('call', 'g', [a, b])` | `(g a b)` |
| `('cond', c, t, e)` / an `if` with two returns | `(if c t e)` |
| a function `g(a, b)` | the term of its body, its parameters as symbols, its recursive calls as `(g ...)` |

### 3.3 Rules
- **Algebra**, with the language's own meaning: `(+ ?x ?y) <=> (+ ?y ?x)`, `(- (+ ?x ?y) ?y) => ?x`,
  `(* 2 ?x) => (+ ?x ?x)`, `(div (* 2 ?x) 2) => ?x`. Careful: `(div (+ (* 2 ?x) 1) 2) => ?x` holds for Python's floor
  division for every x, but for C's truncating division only for x >= 0 (`(2*(-1)+1)/2` is 0 in C, -1 in Python):
  that is why the two divisions are different symbols, and a C rule that needs x >= 0 is not given.
- **Lemmas from our pipeline**, labelled TESTED: a function the pipeline names as gcd becomes
  `(g ?a ?b) => (gcd ?a ?b)`.
- **Known equivalent forms** from the knowledge base, with costs: `(gcd ?a ?b) => (gcd-euclid ?a ?b)`,
  `(gcd ?a ?b) => (gcd-binary ?a ?b)`; Euclid 10 < binary 20 < subtraction 100.

### 3.4 Report and examples
Per file: `is` (the start term equals a known algorithm), `is not` (saturation ends with no known form), or
`cheaper equivalent` (the extraction differs from the start), each marked PROVED (algebra only) or TESTED (a lemma
from behaviour was used).

The two handover examples are the first tests:
1. Heap index algebra: `(/ (- (+ (* 2 i) 1) 1) 2)` -> `i`, PROVED.
2. Subtraction gcd `(if (= a b) a (if (> a b) (g (- a b) b) (g a (- b a))))`, named gcd by the pipeline ->
   `cheaper equivalent: gcd-euclid`, TESTED.

Then run the report over the Rosetta files the pipeline already evaluates; it never changes an answer. Acceptance:
both examples as stated, no crash on any file, a time limit respected on every file, and a short result table in
`docs/04_LEARNING_DESIGN.md` (a new section 20).

---

## 5. Order, time, and stop rules

| Step | Depends on | Time | Check |
|---|---|---|---|
| 0.1 to 0.4 baseline | | 0.5 day | full check equal to committed results |
| 1.1 front ends | 0.3 | 3 days | snapshot identical, then full check identical |
| 1.2 inference limits | 1.1 | 2 days | full check, twice under different load |
| 1.3 archive | 1.1 | 1 day | snapshot identical, all tests incl. polyglot's |
| 2.1 characters + generator rule + string inputs | 1.3 | 1 week | method |
| 1.4 merge runners | 2.1 | 1 day | no fallback answer lost |
| 2.2 helper rule + A.2 + A.3 | 2.1 | 3 days | method; owner decision on fibonacci-2.c |
| 2.3 C structs and pointers | 2.2 | 2 weeks | method; PostgreSQL/GTK outside check |
| 2.4 Haskell | 2.1 | 2 weeks | method |
| 2.5 Lisp | 1.3 | 1 week | method |
| 2.6 Python libraries, no input | 2.1 | 1 week | method |
| 2.7 battery shapes | 2.1 | 3 days | method |
| 2.8 matcher order | 1.2 | 3 days | method; segment_tree matches itself |
| 3 egg first step | 1.3 (pure functions), 2.1 | 1 to 2 weeks | the two examples; no answer changes |

**Stop rules.** A step that fails the method after one fix is dropped and recorded; the next step still runs if it
does not depend on it. Phase 1 must finish before phase 2 (its checks are the base for everything after). If the
full check of 0.2 does not reproduce the committed results, stop and fix the environment or the script first.

---

## 6. What to update after every kept step

- `benchmark/` results (README section 4: a to d; the fallback left-out list after 1.4 uses the merged runner).
- `docs/HANDOVER.md`: section 2 (numbers), 6 (dropped ideas: mark re-added ones), 7 (the upgrade list: mark done,
  recount), 9 (where things are, after 1.1 and 1.3).
- `docs/04_LEARNING_DESIGN.md`: a numbered section per step (20.x), as section 19 did.
- `docs/CONVERSION_FIX_PROMPTS.md`: one prompt per problem with its solution, or its reason for being dropped.
- `README.md`: the results table when numbers change.
- This file: the progress log.

---

## 7. Commands in one place

```
python tools_manual/check/verify_data.py                                  # data unchanged
python tools_manual/check/nf_snapshot.py OUT.json                         # (new in 0.3) snapshot
python tools_manual/check/nf_snapshot.py --compare A.json B.json          # 0 files differ for a refactor
tools_manual/check/fullcheck.sh COPY NAME OUT_DIR                         # the full check, about an hour
python -m unittest tests.test_NAME                                        # each test file; test_frontends alone
python -m unittest discover polyglot_logic/tests                          # the base system's tests (1.3)
./analyze.sh FILE                                                         # one file end to end
```

Report rebuild (README section 4):

```
python eval_ta.py data/TheAlgorithms-Python --learn
python eval_ta.py data/TheAlgorithms-Python --run
python eval_ta.py data/TheAlgorithms-Python --heldout data/rosetta
python tools_manual/decide_new_or_known.py data/rosetta held_files.json benchmark/held_decided.json --v03
python eval_proposed.py benchmark/held_decided.json benchmark/corpus_decided.json
python eval_decision.py benchmark/held_decided.json benchmark/corpus_decided.json node
python final_report.py data/TheAlgorithms-Python benchmark/held_decided.json
```

---

## 8. Progress log

Mark each step when it is done (date, commit, result) or dropped (date, reason, where recorded).

| Step | Status | Date | Commit | Result |
|---|---|---|---|---|
| plan written | done | 2026-10-21 | | this file |
| 0.1 inputs | | | | |
| 0.2 full check on unchanged code | | | | |
| 0.3 nf_snapshot | | | | |
| 0.4 baseline recorded | | | | |
| 1.1 one front end per language | | | | |
| 1.2 inference limits | | | | |
| 1.3 archive dead code | | | | |
| 2.1 characters, generator rule, string inputs | | | | |
| 1.4 merge runners | | | | |
| 2.2 helper rule, A.2, A.3 | | | | |
| 2.3 C structs and pointers | | | | |
| 2.4 Haskell laziness, Maybe, monads | | | | |
| 2.5 Lisp | | | | |
| 2.6 Python libraries, no input | | | | |
| 2.7 battery shapes | | | | |
| 2.8 matcher order | | | | |
| 3 egg first step | | | | |

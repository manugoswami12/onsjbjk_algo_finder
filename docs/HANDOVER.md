# Handover: ONSJBJK Algorithm Finder (closed for now)

This document is for whoever picks the project up next, person or AI. It says what the system is, where it stands,
how to change it safely, what was tried and dropped (with the reasoning), and what to upgrade next.

Last commit of this phase: branch `claude/wizardly-darwin-lb95nf`. Design history: `docs/04_LEARNING_DESIGN.md`
(section 19 is the latest work). Every fix as a re-runnable prompt: `docs/CONVERSION_FIX_PROMPTS.md`.

---

## 1. What it is

A deterministic algorithm finder. Give it a program in Python, C, Common Lisp or Haskell; it names the algorithm, or
says what the program computes ("a sort", "a gcd"), or says UNKNOWN. It does not use machine learning and never runs
the program: it converts the program to Prolog facts and SWI-Prolog decides.

It learned from TheAlgorithms/Python (1346 files) and is tested on Rosetta Code files it never saw (450 files in four
languages).

## 2. Results at close (files the system can evaluate)

The 239 held-out files the system cannot evaluate yet (fragments, broken source, missing packages, language features
not supported yet) are left out of these numbers by decision; they are the upgrade list in section 7.

| | evaluated | correct | wrong | not named (UNKNOWN) | precision | recall |
|---|---|---|---|---|---|---|
| Learnt code (TheAlgorithms/Python) | 1344 | 1344 | 0 | 0 | 100% | 100% |
| New code (Rosetta, never learned) | 211 | 189 | 0 | 22 | 100% | 89.6% |

New code per language:

| language | evaluated | correct | wrong | precision | recall |
|---|---|---|---|---|---|
| C | 35 | 32 | 0 | 100% | 91.4% |
| Common Lisp | 48 | 46 | 0 | 100% | 95.8% |
| Haskell | 43 | 36 | 0 | 100% | 83.7% |
| Python | 85 | 75 | 0 | 100% | 88.2% |

Precision has been 100% (no wrong answer) on both sets since the fixes of section 19; every change since was kept only
if that held. Two full evaluations of the same code give identical results (section 19.16).

## 3. How it works (one page)

1. **Read the program** with tree-sitter (the parser for all four languages). The language's own tools validate it:
   GHC's parsed AST and types for Haskell, clang's JSON AST for C, Python's own `ast`/compiler flags for Python.
2. **Convert to Prolog facts** (the "normal form"): functions, parameters, statements, assignments, returns, calls,
   loops, guards. The same algorithm gives the same facts in every language.
3. **Place it in the tree** of algorithm families (`prolog/families_v02.pl`): its deepest node, e.g.
   `sequence_transformation>comparison_driven_reordering`.
4. **Decide in tiers** (`prolog/decide.pl`), first that holds wins:
   1. file rule (a fingerprint of one TheAlgorithms file),
   2. hand-built branches,
   3. traced logic (exact logic match against learned patterns, literal view first, canonical view second),
   4. learned branches at the file's node,
   5. canonical logic,
   6. behaviour (input/output on a fixed battery of test inputs, run in Prolog on the normal form, never the source).
   "Trace logic is primary, input/output is the fallback." Behaviour also vetoes a logic match it contradicts.
5. **Fallback** (separate, never changes a pipeline answer): a class relation ("sorting", "gcd") checked on every
   battery input of the file's root functions (`tools_manual/decide_new_or_known.py`, `eval_decision.py`).

Main files: `eval_ta.py` (pipeline), `learn_facts.py` (facts), `crosslang_frontends.py` (installs every front end and
rule), `haskell_core_pnf.py` (Haskell through GHC Core), `behaviour_v04.py` + `prolog/interp_v04.pl` (behaviour runner
and interpreter additions), `lowering_v05.py` (the closing round's lowering rules), `polyglot_logic/` (the base
system: never edited, only extended from our layer).

## 4. The working rules (keep them)

These are the owner's rules for this project; every change so far followed them.

- No machine learning. Never execute the source; only the Prolog normal form is evaluated.
- Prefer UNKNOWN to guessing. A wrong answer is worse than no answer.
- No hard coding and no rules written from the test set. A fix is a rule of the language (C, Python, Haskell, Lisp
  semantics), never a rule about one algorithm or one file.
- Keep the hand-built rules; express rules in Prolog where possible. Specific rules before general ones.
- tree-sitter stays the parser; the language's own tools (GHC, clang, Python's ast) are used to validate and to supply
  information (types, names, scopes).
- Trace logic is the primary evidence; input/output is the fallback. Keep both.
- `polyglot_logic/` is not edited; extend it from our layer (subclass or patch at install time).

## 5. How to make a change safely (the method)

1. Work in a **copy** of the repository, with everything in it:
   `mkdir COPY && tar cf - --exclude=.git . | (cd COPY && tar xf -)`
   (Do not exclude by folder name: `--exclude=benchmark` also drops `polyglot_logic/benchmark` and the runs crash.)
2. **Hand-test** the rule first on small programs whose results you work out by hand, plus a near negative, plus the
   real file it is for. Add them to `tests/`.
3. **Full check**: `tools_manual/check/fullcheck.sh COPY NAME OUT_DIR` (about an hour). It relearns, reruns
   TheAlgorithms and the held-out files, and compares with the committed results:
   - learnt answers must not change (1344/1344, 0 differences);
   - no previously correct held-out answer may be lost, no new wrong answer may appear;
   - tree nodes old against new: every change explained;
   - any traceback in the logs makes the run invalid.
4. If one previous success fails or a wrong answer appears: **try one fix**; if it does not work, **drop that idea**
   and record it (doc 04 section 19, `docs/CONVERSION_FIX_PROMPTS.md`, "Tried and dropped").
5. If kept: run all `tests/`, rebuild the report (`README.md` section 4 steps b–d; the left-out list uses the
   documented `--v03` runner), update docs, commit.

Run one full check at a time: the AP13 scan has a 120 s wall-clock limit per call, so a second heavy job on the same
machine can push a borderline file over it.

## 6. What was tried and dropped, with the reasoning

Each of these broke a previous success or added a wrong answer, one fix was tried, and the idea was dropped. They
are the first things to revisit, in the order given, once their blocker is solved.

### 6.1 A Python generator passed straight into a call (19.17) — revisit first

**What the rule did.** It made `sum(int(c) for c in str(n))` run the way Python means it (one comprehension
argument; the rule already existed in the old v0.3 runner, `pnf_v03.py`). Before, that line was lowered as junk, so any
function using it did not run and gave no evidence either way.

**Why it caused trouble.** The rule itself is correct, but it let functions run that expose an older weakness of the
interpreter: characters are stored as their number codes, so `'7'` is stored as 55. When `int(c)` gets the character
`'7'`, it cannot tell it from the number 55, and returns 55.
- TheAlgorithms' `happy_number` uses exactly this line, so it then ran with wrong values; its wrong behaviour clashed
  with `is_power_of_two`, which was lost (a learnt answer).
- TheAlgorithms' `perfect` also started running; its real difference at input 0 then vetoed the logic match that
  names perfect-numbers-1.hs and perfect-numbers-3.py (two correct answers lost).
- The primality files started running and matched `next_prime_number`'s helper (new wrong answers).

**Why it is dropped and not fixed.** The real fix is to give characters their own value, separate from numbers. That
touches every string operation in the interpreter (`interp.pl`, `interp_v03.pl`, `interp_v04.pl`: indexing, slicing,
comparison, `ord`/`chr`, `int`, `str`, `join`, the battery's string inputs), so it is not a single targeted fix. Under
the rule (one fix attempt, otherwise drop), it was dropped.

**Upgrade path.** (1) Represent a character as `char(Code)` in the interpreter, a string as a list of `char/1`;
`int(char(C))` reads the digit, `ord`/`chr` convert. (2) Then re-add the generator-argument rule (appendix A.1; the same rule is in
`pnf_v03.PNFv03.expr`). (3) Then add string inputs to the battery (many Python, C and Lisp files wait on them, see 7).

### 6.2 A C declaration without a value, `int i;` (19.17)

**What the rule did.** `int i;` and `int t, k;` were lowered as a *read* of the variable, so even
`int t; t = n * 2; return t;` failed with `unbound(t)`. The rule lowers such a declarator as nothing, as C means it.
The tree side already skips it; only the behaviour side was wrong.

**Why it caused trouble.** The conversion became right, and two C files started running and were named by behaviour
that is true but labelled otherwise: `fibonacci-sequence-2.c` (its `fibb` is the Fibonacci recurrence with a shifted
start) was named `climbing_stairs`, and `sorting-algorithms-pancake-sort-2.c` (it holds only `do_flip`, the reversal
helper; the sort is in another snippet) was named `reverse_array`.

**Why dropped.** Neither is a conversion fault, so no conversion fix exists; the label comes from the answer tiers.
The one general tier fix ("only a file's roots name it") was tried earlier and moved 248 learnt files. Dropped.

**Upgrade path.** A tier rule for "a file whose only functions are helpers" (no root that computes the whole task),
or a Fibonacci-family alias that treats shifted Fibonacci recurrences as one label; then re-add this rule (appendix A.2).
It unblocks about 16 C files.

### 6.3 The Haskell Core reader's operator tokens (19.17)

**What the rule did.** It read `()` (unit), an operator definition `(!)` and class methods like `$c+_aTa` as names, so
8 Haskell files that GHC accepts became readable (factorial-9.hs then ran correctly).

**Why it caused trouble.** `fibonacci-sequence-16.hs` became readable too; its root `fib` cannot run (it needs a `Num`
instance for matrices), but its matrix helpers `<+>` and `<*>` ran, and a helper's behaviour named it `round_robin`.

**Why dropped / upgrade path.** Same tier issue as 6.2 (a helper naming a file whose root does not run). Fix the tier
rule, then re-add the tokens (appendix A.3).

### 6.4 Earlier dropped ideas (section 19, still valid)

- A null input (0, []) as "no evidence" (19.12): fixed perfect-numbers-1.hs by hand but lost six learnt answers
  (signum, not_gate, stooge_sort, ...): for them the null input *is* the algorithm.
- The exact-logic tier on the tree's facts as a whole (19.13): 19 learnt answers lost; solved instead as two views
  (literal first, canonical second).
- A "table of library names" for mixed files, and naming a match by the matched function (19.x): test-set rules.
- `+` on lists as concatenation without types, in the facts (removed): every `+` of a recursive result became a join.
  (At run time the interpreter knows the values, so list + list there is exact and is used.)
- Placing a file's label only at its roots' nodes: moved 248 learnt files.

## 7. Upgrade list: the 239 files left out, by cause

Measured by running every left-out file through the pipeline and taking each one's first blocker (section 19.17;
counts from the 242-file analysis, 3 of which are now evaluated). Fixing a first blocker can reveal a second one.

**Not real programs (about 67): leave out.** 55 fragments (GHCi/REPL transcripts, a call of a function defined in
another snippet, imports only, code GHC says uses undefined names), 6 broken sources (typos, Python 2), 6 missing
Haskell packages (`Data.MemoTrie`, `Data.CReal`, `Data.List.Split`, ...).

**Our own conversion (most fixed in 19.17; still open):**
- C declarations without a value (about 16): blocked by 6.2.
- Haskell Core reader (8): blocked by 6.3; `josephus-problem-1.hs` also has a nested `let` the parser misreads.
- Python generator argument (3): blocked by 6.1.
- Haskell: three local definitions lost by the lowering (`wild_X1`, `perfect`, `primeNums`).

**Language support to add (about 120), in suggested order:**
1. **Characters as their own values, and string inputs in the battery** (6.1): unblocks Python string code (caesar,
   palindromes, run-length, roman numerals), Haskell `digitToInt`/`show` code and Lisp string code.
2. **Haskell laziness for infinite lists** (about 16): `fibs = 0 : 1 : zipWith (+) fibs (tail fibs)`, `[1..]`,
   `iterate`, `cycle`, `enumFromThen`. Idea: evaluate a top-level infinite list only as far as a battery-sized `take`.
3. **Haskell `Maybe`, `Ordering` and arrays** (about 6): `unfoldr`, `maybe`, `compare`, `maximumBy`, `Data.Array`.
4. **Haskell monads** (about 9): `IO`, `ST` with `STUArray`, `foldM`, `>>=`.
5. **C pointers** (about 9): pointer arithmetic (`a + i`), `*p`, `&x`, structs, strings; `goto`.
6. **Lisp** (about 7): `loop ... with/and/nconc`, `&key`, `complement`, `mapc`, `multiple-value-list`, reader macros.
7. **Python**: `itertools.cycle`/`groupby`, `heapq.merge`, numpy, `complex`; functions with no input (endless
   generators, top-level scripts) need a "no-input" convention.
8. **Battery shapes** (about 11): tuple arguments, a list plus its length passed separately, inputs a program
   legitimately rejects (base 0).

**Known system issues (not blocking, worth fixing):**
- The AP13 matcher's result depends on the order of tabled answers (`polyglot_logic/prolog/canon.pl` tables
  `under/2`, `reaches/2` and the matcher keeps the first solution). Since 19.16 the order is fixed (single-threaded
  GC), so results are repeatable, but in the fixed order `segment_tree.py` does not match its own pattern: a search
  over all orders would find matches it now misses.
- The 120 s wall-clock limit per Prolog call (`polyglot_logic/tools/env_run.py`): problem_111's canonical scan hits
  it every time. An inference limit would be load-independent.
- Two behaviour runners exist: the pipeline's (`behaviour_v04.py`) and the fallback's documented v0.3 runner
  (`pnf_v03.py`, used by `--v03`). They differ (v0.3 has the generator rule, v0.4 has the 19.17 rules). Merging them
  would make the left-out list and the pipeline agree.

## 8. Frozen inputs (so results can be reproduced)

Upstream code and tools change; the results here were measured with exactly these.

- **Data, in the repository, never updated from upstream** (`data/README.md`): TheAlgorithms/Python, 1736 files at
  commit `e1a2a8b0`; Rosetta Code, 494 files (C 76, Common Lisp 85, Haskell 157, Python 176; the 450 held-out files
  among them) at RosettaCodeData commit `1d475861`; the task labels `polyglot_logic/benchmark/rosetta_truth.json`.
  Every file's sha256 is in `data/MANIFEST.sha256`; `python tools_manual/check/verify_data.py` checks them (it ends
  with `all match the tested data`). A newer upstream version is a new data set, measured beside this one.
- **The parser, in the repository**: tree-sitter 0.26.0 and its 8 grammars, prebuilt and with source and checksums, in
  `vendor/tree-sitter/` (install with `python vendor/tree-sitter/install_offline.py`).
- **Tools, not in the repository; the tested versions**: Python 3.13.16, SWI-Prolog 9.0.4, GHC 9.4.7, ECL 21.2.1,
  clang 18.1.3 (Ubuntu). Another version may give different facts or runs (GHC's Core output in particular changes
  between releases): rerun the full check (section 5) before trusting results with other versions.

## 9. Where things are

| What | Where |
|---|---|
| Results | `benchmark/FINAL_REPORT.md`, `benchmark/ta_answers.json`, `benchmark/ta_heldout.json` |
| Design and history | `docs/04_LEARNING_DESIGN.md` (section 19 = this phase) |
| Every fix as a prompt | `docs/CONVERSION_FIX_PROMPTS.md` |
| Hand rules and their prompts | `docs/HAND_RULE_PROMPTS.md`, `docs/RULE_PROMPTS.md`, `docs/HAND_RULES_WRITTEN.md` |
| Full check | `tools_manual/check/fullcheck.sh` |
| Data check | `tools_manual/check/verify_data.py`, `data/MANIFEST.sha256` |
| Tests | `tests/` (run each with `python -m unittest tests.test_NAME`; `test_frontends` alone) |
| Analyse a file (one command) | `./analyze.sh FILE` or `analyze.cmd FILE` (`analyze.py`; what it learns is cached in `.cache/`, rebuilt when code or data change) |
| How to install and run | `README.md` |

---

## Appendix A: the code of the three dropped rules

They were never committed (each was dropped in a scratch copy before the commit), so their exact code is kept here,
ready to re-add once the blocker in section 6 is solved. Each goes into the place named; then run the full check.

### A.1 Python generator as a call's only argument (`lowering_v05.py`, inside `expr`, Python branch)

```python
            if node.type == 'call':
                args = node.child_by_field_name('arguments')
                if args is not None and args.type == 'generator_expression':
                    out = expr0(self, node)
                    if isinstance(out, tuple) and out[:1] == ('call',):
                        return ('call', out[1], [self.comp(args)])
                    return out
```

### A.2 C declarator without a value (`lowering_v05.py`, first lines of `st`)

```python
        if self.lang == 'c' and node is not None and node.parent is not None and node.parent.type == 'declaration' \
                and node.type in ('identifier', 'array_declarator', 'pointer_declarator') \
                and node is not node.parent.child_by_field_name('type'):
            if node.type == 'identifier' or node.child_by_field_name('declarator') is not None and \
                    node.child_by_field_name('declarator').type == 'identifier' and node.type == 'pointer_declarator':
                return ('skip',)
```

### A.3 Haskell Core reader tokens (`haskell_core_pnf.py`, `TOKEN` and `tokenize`)

In `TOKEN`, before the `punct` group, and the method-name suffix in the `name` group:

```
| (?P<opname>\(\)|\([!#$%&*+./<=>?^|~:\\-]+\)) | (?P<punct>...)
| (?P<name>\$[A-Za-z0-9]*[!#%&*+./<=>?^|~:\-\\]+(?:_[A-Za-z0-9]+)?|...)
```

In `tokenize`, where a token is appended:

```python
        kind, word = m.lastgroup, m.group()
        if kind == 'opname':                 # (!) as a binder is the name ! (GHC writes its uses as !); () the unit
            kind, word = 'name', word if word == '()' else word[1:-1]
        if kind not in ('ws', 'cast', 'co'):
            toks.append(Tok(kind, word, m.start() - (text.rfind('\n', 0, m.start()) + 1)))
```

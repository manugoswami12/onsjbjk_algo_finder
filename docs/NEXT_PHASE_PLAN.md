# Next phase plan: implementing the handover

Written at close, to be read with `docs/HANDOVER.md` (sections 4 and 5 are the rules and the method for every
step). Each phase ends with the checks under Verification; a step that fails them gets one fix, else it is dropped and
recorded, as the handover says.

## Context
Owner's decisions (at close): scope = the whole plan (phases 0 to 3, stopping wherever a step fails the method);
dead code is archived in `older_code/archive/`, not deleted; this plan lives in the repository.

PR #1 is merged (main = e792dfd). The handover's next phase is: clean up first (10.1), then the upgrades (6, 7), then
egg (10.3). After a reset the next session starts with no memory, so this plan is self-contained: read
docs/HANDOVER.md first, keep its working rules (section 4) and its method (section 5) for every step.

Facts found while planning (read-only):
- Behaviour patch chain, all installed by `crosslang_frontends.install()` in this order: wrap `io_trace.normal_form`
  (Haskell -> haskell_core_pnf, C -> cpp-expanded text), `lowering_v03` (Lisp loop `finally`, C `x op= y`),
  `returns_function` (facts and behaviour), `lowering_v05` (19.17 rules), `generators`, `behaviour_v04` (runner and
  kinds). Facts side: `learn_facts` (single-threaded-GC wrapper on env_run.run, returns_function for facts).
- Two runners: `behaviour_v04` (pipeline) and `pnf_v03` (used by `decide_new_or_known --v03`, `ta_classes`,
  `analyze.py`'s fallback). `interp_v04.pl` loads `interp_v03.pl` loads AP13 `interp.pl`.
- 12 of 55 of our Python modules are not reached from any entry point or test: cmp_nodes (used by fullcheck.sh, keep),
  corpus_roots, ecl_witness, eval_crosslang, eval_crosslang_ext, eval_ecl, eval_ecl_staged, eval_heldout, eval_learn,
  eval_library, popper_fallback, ta_prompts; several are cited in older docs (ECL design, HAND_RULE_PROMPTS,
  RULE_PROMPTS, README_v02_details), so "not reached" is not "unused".
- `older_code/` (2.2 MB): `polyglot_logic` still loads `algo_reference_corpus/ap12/prolog/route_extended.pl`,
  `algo_reference_corpus` (knowledge_store), `semgrep_prolog_poc/tools` (fact_io); `prolog/ecl_main.pl` loads
  route_extended.pl; polyglot's test_ap13 uses examples from the PoC folders.
- Wall-clock limits: 29 timeouts in our code; the critical one is env_run.swipl's 120 s (AP13 scan), plus
  haskell_core_pnf 90 s, logic_canon 120 s, ecl 120 s, learn_apply 3600 s. Behaviour jobs already use inference limits.
- Rust (cargo, rustc) is installed: egg can be built here.

## Phase 0 — baseline (half a day)
1. Start from the latest main on the session's branch: `git fetch origin main && git checkout -B BRANCH origin/main`
   (a merged pull request is finished; new work is a new pull request).
2. `python tools_manual/check/verify_data.py` must say all match.
3. Run `tools_manual/check/fullcheck.sh` on an unchanged copy (it was syntax-checked but never run from its repo
   location): learnt 0 differences, new code 173 pipeline-correct / 0 wrong, tree nodes 0 changed. This also creates
   the baseline node file. If it fails, fix the script first.
4. New fast check for refactors, `tools_manual/check/nf_snapshot.py`: dump, for all 1796 files, the tree facts
   (learn_facts.tree_facts), the behaviour normal form (io_trace.normal_form) and the battery runs
   (io_trace.run_functions) to one JSON; compare two snapshots. A pure refactor must give a byte-identical snapshot
   (minutes, not an hour). Commit it with a test.

## Phase 1 — clean-up (handover 10.1); results must not move
Order chosen so each step is checkable and later steps run on a cleaner base.

1.1 Fold the patch layers into one front end per language (pure refactor).
   - New package `frontends/`: `python.py` (a PNFLowerer subclass holding lambda, returns_function, generators,
     constants, unpacking), `c.py` (cpp expansion, effects, arrays, casts, literals, `/` `%`, strlen), `lisp.py`
     (a LispPNF subclass: loop `finally`, case, subseq, &optional, last, map), `haskell.py` (haskell_core_pnf moved),
     `runner.py` (behaviour_v04), `install.py` (one place that swaps our subclasses in: the single patch point is
     io_trace.normal_form constructing our subclass; no method patching of AP13 classes).
   - Facts side: fold returns_function's ImperativeLowerer patch into imperative_logic.py's own subclass.
   - Old module names stay as thin re-exports for one phase (crosslang_frontends.install, lowering_v05.install, ...)
     so docs, prompts and tests keep working; remove them in 1.3.
   - Check: nf_snapshot byte-identical; all tests; then one full check (0 differences in answers AND evidence).

1.2 Inference limits instead of wall-clock limits.
   - Measure first: run the full pipeline with every swipl call wrapped in `statistics(inferences, ...)` logging
     (scratch only), so the limit is set above every call that succeeds today.
   - In our layer (learn_facts' env_run.run wrapper, already the single swipl entry), wrap each goal in
     `call_with_inference_limit(Goal, N, R)` with N from the measurement; keep a large wall-clock (30 min) only as a
     safety net. Same for GHC/ECL subprocess limits where they are Prolog; external compilers keep a generous timeout.
   - Expected change: calls that time out today (problem_111's canonical scan) may now finish or fail by inference
     count; that can change evidence. Full check: answers must not lose a success or gain a wrong answer.

1.3 Archive dead code (the owner's decision: archive, not delete).
   - Keep: everything reachable from analyze.py, eval_ta.py, final_report.py, eval_decision.py, eval_proposed.py,
     ta_distinct.py, tools_manual/decide_new_or_known.py, write_branches.py, tools_manual/check/*, tests/*.
   - The 11 unreached modules: keep the ones a current doc tells you to run (eval_learn for the staged run,
     ta_prompts for RULE_PROMPTS); move the rest to `older_code/archive/` with a short README saying what each was
     for and why it is archived. older_code/: keep in place exactly the files polyglot_logic and ecl_main.pl load
     and the examples polyglot's tests read; move the rest to `older_code/archive/`. Update the docs that cite moved
     scripts.
   - Remove the re-export shims of 1.1.
   - Check: nf_snapshot identical; all tests including polyglot_logic/tests; full check.

1.4 Merge the two behaviour runners — after 2.1 (it depends on it).
   - Today the fallback (v0.3) answers primality-1/2.py only because v0.3 has the generator-argument rule, which the
     pipeline dropped (handover 6.1). Merging before 2.1 loses those two answers. So: do 2.1, then make
     pnf_v03.run_functions delegate to frontends.runner, make decide_new_or_known / ta_classes / analyze use one
     runner, rebuild the left-out list and report. Check: no fallback answer lost, 0 wrong.

## Phase 2 — upgrades (handover sections 6 and 7), each by the method
2.1 Characters as their own values (6.1, unblocks the most).
   - Interpreter: a character is `char(Code)`, a string a list of `char/1`; update indexing, slicing, comparison,
     `ord`/`chr`, `int`/`str`/`join`, `isalpha`..., `upper`/`lower`, `zfill`, Haskell `digitToInt`/`show`, Lisp
     strings, C `strlen`/char arithmetic (C chars stay integers: C semantics), in interp_v04 (our layer).
   - Hand tests: `int('7') == 7`, happy_number on 7 is true, caesar on a string, C `'a' + 1`.
   - Then re-add the generator-argument rule (handover appendix A.1); check happy_number, is_power_of_two,
     perfect-numbers-1/3, primality-1/2 behave as Python does.
   - Then string inputs in the battery (new signature kinds; changes fingerprints: full check must show only new
     evidence, no lost answers). Then do 1.4.
2.2 The helper tier rule (6.2, 6.3, and the PostgreSQL case of 10.2): a function that is only a helper (called by a
    root, or a one-line formula) cannot name a file whose roots do not run; the file answers UNKNOWN or names the
    part ("contains a binary heap's index arithmetic"). Re-add appendix A.2 (C declarations, ~16 files) and A.3 (Core
    tokens, 8 files); check fibonacci-2.c, pancake-sort-2.c, fibonacci-16.hs give no wrong answer.
2.3 C structs and pointers (the support that matters for real code, 10.2): struct fields as named cells of a record
    term, `->` and `.` access, pointers to array cells (base + offset), `*p`, `&x`, malloc'd structs; the battery
    gets no struct inputs, so a root taking a struct pointer stays unrunnable unless built inside. Test on the
    PostgreSQL binaryheap.c and GTK gtkrbtree.c of 10.2 as an outside check (not scored).
2.4 Haskell: laziness for top-level infinite lists (evaluate to a battery-sized `take`), then Maybe/Ordering/arrays,
    then monads (IO as effects, ST/STUArray as array cells). 2.5 Lisp (loop with/and/nconc, &key, complement, mapc,
    multiple values). 2.6 Python libraries (cycle, groupby, heapq.merge) and a no-input convention. 2.7 battery
    shapes (tuples, list plus length by usage).
2.8 System: the matcher's order dependence (handover 7, known issues) — in our layer, rerun a scan that misses with
    the reference set in reverse order and keep the union only if both orders are consistent; full check.
After each: rebuild the report (handover 5.5), update HANDOVER sections 2/6/7 and CONVERSION_FIX_PROMPTS (a prompt per
problem with its solution; dropped ideas with reasoning), commit.

## Phase 3 — egg (handover 10.3), first step only
1. `tools_manual/egg/` Rust crate on `egg` (vendored with `cargo vendor` and a checksum, like tree-sitter, so it is
   frozen): reads S-expressions and rules, saturates with node and time limits, extracts by a cost function, prints
   the best term and whether the start term was proved equal.
2. `egg_export.py`: pure functions only (Haskell Core functions first, then Python/C functions with no stores or
   loops) from the normal form to S-expressions; loops and assignments are skipped until an SSA step exists.
3. Rule sets: algebra (integer arithmetic identities) and lemmas from our pipeline ("f is gcd", marked TESTED, from
   recognised answers), plus the knowledge base's equivalent forms (gcd-euclid, gcd-binary) with costs.
4. Report per file: is / is not / cheaper equivalent (tested or proved). Worked examples from the handover: heap
   index algebra, subtraction gcd -> Euclid. Evaluate on the Rosetta files already evaluated; no change to answers.

## Verification (every step)
nf_snapshot identical for refactors; fullcheck.sh: learnt 1344/1344 with 0 differences, no correct held-out answer
lost, 0 wrong (pipeline and fallback), tree nodes explained, no traceback; all tests; verify_data; analyze.sh on an
own file and one held-out file per language from a fresh clone; two full evaluations identical.

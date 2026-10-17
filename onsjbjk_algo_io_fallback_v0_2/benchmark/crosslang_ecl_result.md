# Common Lisp through ECL: Lisp -> ECL C -> v0.2 facts -> prolog/route_v2.pl

ECL (21.2.1) compiles each defun to C (nothing is run). `ecl_witness.py` reads ECL's fixed C shapes as the
same facts the Python witnesses emit (linear_self_product, self_calls_minus_one_minus_two, modulo_recurrence,
digit_decomposition, element_exchange, comparison_controls_exchange, ...); the unchanged Prolog router branches.
No learning, no behaviour runs: knowledge = the v0.2 branch rules built for Python.

| Stage | Precision | Recall | Wrong on negatives |
|---|---|---|---|
| clean: 3 never-used functions (quicksort, topo-sort, naive-match) | 1/1 | 1/1 | 0/2 |
| all 21 functions of the frozen key (most inspected earlier, not held-out) | 4/5 = 80% | 4/9 = 44.4% | 0/12 |

Found: naive-fib (fibonacci_like), insertion-sort and heapsort and quicksort (sorting). selection-sort got only
the broad sorting family (no ECL min-index shape yet: counted WRONG against its narrow label).
Missed (no ECL shape written yet): bin-search, bin-search-v0 (midpoint interval), mat-max (2-D best-so-far),
merge-sort (list consing).

## Method 2: ECL C traced by the AP13 Prolog rules (same rules as every language)

Design: `docs/03_V02_ECL_LOGIC_DESIGN.md`. Lisp -> ECL C (`ecl_compile.py`) -> AP13 neutral facts via the
unchanged AP13 C lowerer plus tree-sitter label/goto markers (`ecl_facts.py`) -> `prolog/ecl_norm.pl`
(operator table, basic-block symbolic execution, back-edge loops, control-dependence guards, recursion) ->
unchanged AP13 `roles.pl` / `families.pl` -> `prolog/family_to_v02.pl` -> `route_v2.pl`.
No learning, nothing run.

Logic tests on own programs (`tests/test_ecl_logic.py`): 19/19 (13 algorithms, 6 near misses with no branch).
v0.2 selftest 47/47. ruff clean, pylint 10/10 (AP13 path imports excluded).

Staged key `benchmark/ecl_staged_truth.json` (85 Rosetta Common-Lisp files at file level + the 21 book
functions; nested seeded stages 3/15/55/101; frozen and committed before the first run).

| Run (stage 3) | Precision | Recall | Result |
|---|---|---|---|
| first run | 1/1 | 1/3 | FAIL |
| retry 1 (top-level forms compiled as `<toplevel>`; scope renaming of re-declared C temporaries) | 2/2 | 2/3 | FAIL |

```
greatest-common-divisor-2.lisp   euclid_like        ok       numeric>recurrence>modulo_recurrence
fibonacci-sequence-3.lisp        fibonacci_like     ok       numeric>recurrence>pair_recurrence   (retry 1)
book:ch5-arrays.lisp::selection-sort  selection_exchange|comparison_driven_reordering  UNKNOWN  sequence_transformation
```

Retry 1 fixed two generic ECL-side omissions: a file with no defun (`(loop for x = 0 then y and y = 1 then
(+ x y) ...)`) produced no C function; ECL re-declares `cl_object v8;` in nested blocks, which merged two
variables into one.

The remaining miss is not ECL-specific. The book's selection sort keeps the best VALUE (`best`) and its index
`idx = i + j + 1`, comparing `vec[i+j+1]` with `best`. The shared rules ask for an index holder compared as
`a[j] < a[m]` and assigned from the loop variable (`m = j`): AP13 `select_extreme` and the v0.2 Python witness
`min_index_then_exchange` alike. So the same function written in Python is missed too. The trace is otherwise
correct (exchange of `vec[i]` / `vec[idx]`, organizer, steppers). Fixing it would mean loosening the shared rules
to fit this test unit, so retry 2 was not spent and testing stopped here as instructed (stages 15/55/101 not
run).

### Continued (after the branching fix): stage 3 PASS, stage 15 PASS, stage 55 FAILED (1 retry left, paused)

| Stage | Run | Precision | Recall | Wrong on negatives | Result |
|---|---|---|---|---|---|
| 3 | retry 2 (`families_v02.pl`: a comparison of the sequence's values decides the exchanged position) | 3/3 | 3/3 | 0/0 | PASS |
| 15 | first | 5/7 | 5/10 | 1/5 | FAIL |
| 15 | retry 1 (closures, local functions, library table, list loops) | 7/7 | 7/10 | 0/5 | FAIL |
| 15 | retry 2 (`loop collect` + fold fusion) | 8/8 | 8/10 | 0/5 | PASS |
| 55 | first | 18/19 | 18/39 | 1/16 | FAIL |
| 55 | retry 1 (see below) | 24/25 = 96.0% | 24/39 = 61.5% | 1/16 | FAIL |

All changes are general (each one also has a logic test on my own program, `tests/test_ecl_logic.py`, 36 cases):
- branch rules (`prolog/families_v02.pl`, language-neutral, AP13 unchanged): comparison-decided exchange
  position -> comparison_sort / select_extreme; pair recurrence through the in-loop reaching definition
- ECL C -> neutral facts: closure cells `lex0[0]` are the captured variable; local functions `LC<k>`; library calls
  (reverse, string=, nconc, remove, bit/sbit, car/cdr macros, list, endp); `truncate` remainder; dolist cursor
  loops -> for-each facts; `loop collect` (rplacd on the tail cell) -> append, and `reduce op` over it fused into the
  accumulator loop (deforestation); new cons cells keep identity; shadowed Lisp names stay distinct;
  `&optional` functions become ordinary functions; induction variables may step by a loop invariant;
  else-guards after a returning then-part (control dependence)
- tree-sitter 0.26: only byte offsets are read (Point / parent access corrupted memory: segfaults)

Stage 55 misses (15) and why:
- no algorithm in the file (3): bubble-sort-2 and sum-digits-2 only call a function of another file; lcm-1 is a
  REPL transcript using the built-in `lcm`
- functional / library idioms not normalised (8): dot-product-1/2 (`apply`/`map`/`reduce`), luhn-2 (curly reader
  syntax), fib-8 (`defmethod` with eql specialisers), fib-9 / fib-10 (growing a list), insertion-sort-1 (`reduce
  #'insert` + `ldiff`), Rosetta merge-sort (built-in `merge`)
- rule coverage (2): sum-digits-1 (base is a parameter; the digit rule wants a constant base), book merge-sort (the
  merge is in a helper the key labels negative)
- book bin-search (`&key` arguments) and bin-search-v0 (RUTILS `slice`) (2)

The wrong negative: caesar-2 `z`. ECL's result register `value0` serves both the `(or (when ..) ..)` expression
and the return value, so it looks like `b := value0; value0 := f(b mod 26)` (a Euclid pair). The proper fix is
splitting value0 into its def-use webs.

Recall 80% at stage 55 needs 32/39. Three units are unanswerable from their file. Reaching 32 needs most of the
functional-idiom group, i.e. new normalisations (`map`/`apply` fusion, `defmethod`, `&key`, `slice`). So the last
retry was not spent; waiting for a decision.

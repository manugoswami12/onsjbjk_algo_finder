# AP13 v2 Pseudocode, Activities and Critical Logic

## 1. Pseudocode (only the parts that change; everything else is as in doc 02)

### G1/G2/G6: lowering (all lowerers share the same new facts)
```python
def after_function_lowered(F):                      # fact_io.FactSet.finish()
    if any(call_at(S, base(name_of(F)), _) for S in stmts(F)):
        L = new_loop(F, 'recursion')                  # G2: recursion is a loop
        for S in stmts(F): add(in_loop(S, L))
        for S, args in self_calls(F):
            rename call -> '$self'
            for k, a in enumerate(args):
                if a != var(param[k]): add(assign(S, var(param[k]), a))   # parameter update
    if loop has no loop_cond and a base-case guard exists: add loop_cond(L, not(guard))

def early_exit(stmt):                                 # G6
    kind in {return, raise, break, continue, assert-fail} inside `if c` with no else
    -> following statements of the same block get guard(c, false)
    assert c  -> following statements get guard(c, true)

docstring / pass / import / global      -> ignored (no fact)
yield e                                  -> ret(e)                       # G1
s.append(x) / push / push_back / add     -> call_at(S, append, [s, x])  # canonical name
```

### G4/G5: element iteration and folds
```python
for x in s:          loop_iter(L, s); loop_var(L, x)
                     canon: every var(x) inside L  ->  elem(s, var(x))
foldl f z xs (Haskell), reduce(f, xs, z) (Python/Lisp), Reduce(f, xs, z) (R):
    acc = z; loop L over xs with element e:  acc = f(acc, elem(xs, e)); result acc
    (lambda bodies are inlined; a named f stays a call)
```

### G1/G3: slice (Prolog `slice.pl`)
```python
effects(F) = exchanges | element writes | appends | ret/yield of non-constant values
for each effect S:
    rel += effect, guards(S), every loop containing S (+ nesting), lvar, lcond
    worklist = names used in effect and guards, minus params / loop vars
    while worklist:
        X = pop
        for D in definitions of X inside ANY loop of the reachable functions:   # G3
            rel += value(D, var(X), E), under(D, L) for its loops, guards(D)
            worklist += names(E)
```

### G7/G8/G9: learning and matching
```python
variabilise(rels):
    names inside var(_)         -> Prolog variables (distinct)
    statement/loop ids          -> Prolog variables
    call(Name, ...) where Name is a function defined in this source -> variable  (G7)
quality(rels) = 'usable' if any under/2 relation and len(rels) >= 4 else 'trivial'   # G8
store reference(Label, Branch, Rels, Names) plus metadata (path, function, quality, group)
group = sha256(variant-normalised clause without label)                          # G9

scan(candidate):
    matches = [r for r in usable refs (branch routed or unknown) if holds(r)]
    sort by (-len(r.rels), label); collapse by group
    report top group first: "IDENTIFIED: path::function  (+ n structurally identical)"
```

### G10: learn a directory
```python
def learn_dir(root):
    for path in sorted(root.rglob('*.py')):                # stable order
        facts = lower(path)                                # one tree-sitter parse
        out = swipl(learn_all_main, facts, label_prefix)   # ONE process per file
        for each LEARN line: store (idempotent; sha conflict -> error, never overwrite)
    print counts: generated, already_present, trivial, no_effects, error
```

### G11: evaluation (`rosetta_eval.py`)
```python
truth = json.load('benchmark/rosetta_truth.json')     # written before the first run
for task, langs in rosetta:
    for file in task/<lang>/*:
        r = scan(file)
        top = first identification; ids = all identifications
        correct(x) = x.source_path in truth[task]
        count top1_correct, any_correct, top1_wrong (with the culprit reference), unknown
print per-language and per-task tables; negatives count only top1_wrong
```

## 2. Activities (new or changed programs)
| Type | Program |
|---|---|
| Transform (shared post-pass: recursion, self-calls) | `tools/fact_io.py` (`FactSet.finish`) |
| Transform per syntax family | `lower_imperative.py`, `lower_sexpr.py`, `lower_equations.py`, `prolog/lower_prolog.pl` |
| Static data (synonyms, append names, fold names) | `tools/lang_tables.py` |
| Logic | `prolog/canon.pl` (element iteration), `slice.pl` (G1/G3), `leaf.pl` (ranking), `main.pl` (`learn_all_main`) |
| Knowledge storage (quality, group) | `tools/knowledge_store.py` |
| User input (`learn-dir`) | `tools/cli.py` |
| Display (ranked identification) | `tools/report.py` |
| Evaluation | `tools/rosetta_eval.py` + `benchmark/rosetta_truth.json` |

## 3. Critical logic (new rows)
| Critical logic | Why critical | Risk | Safeguard |
|---|---|---|---|
| Recursion post-pass | base for slice, evidence and leaf in all languages | false loops, for example through mutual recursion | self-calls only; facts tests |
| Element-iteration rewrite | base for all accumulator and search references | rewrites a variable that is not the element | only the declared foreach variable, only inside its loop |
| Quality gate | decides what is matched | too loose → false identifications; too strict → recall loss | measured and reported in the B4 tables |
| Ranking and grouping | user-visible answer | wrong top-1 | false identifications listed with their culprit reference |
| swipl batch learn | runs once per file over 1,608 files | one bad file aborting the run | per-file catch: error row + continue, counted |

## 4. Problems found while measuring v2, and how each was solved
Every fix is general and not tied to any one file. Each was found on the corpus or on
the held-out set, then checked against the v1 and v2 tests.

| # | Observation | Cause | General fix |
|---|---|---|---|
| Q1 | `game_of_life.__judge_point` "matched" sorts, sieve and Levenshtein | the reference was only "return x inside two loops"; no computation was traced | quality gate: at least 2 content relations, OR an accumulator recurrence, OR a recursive computation |
| Q2 | `maths/factorial.py` failed to identify factorials | `if n < 0: raise ...` became a guard on every later statement | `raise`/`throw`/`assert` exits are error handling, not control dependence (only `return`/`break`/`continue` are) |
| Q3 | `return abs(b) if a == 0 else gcd(b % a, a)` was opaque | conditional expressions were not lowered | returned/assigned conditionals become two guarded statements; elsewhere `cond(c, a, b)` |
| Q4 | `return abs(x)` after a loop was rejected as "delegation" | the delegation rule was too broad | only a call whose arguments are untouched inputs or constants is a delegation |
| Q5 | `main` and other wrappers became duplicate references | effects were inherited from callees | a function is learned only if it computes something itself |
| Q6 | `x, y = y, x % y` was never traced | tracing stopped at every parameter | only *untouched* parameters stop tracing |
| Q7 | `gcd(b % a, a)` vs `gcd b (a mod b)` vs `gcd(b, a % b)` | argument order, base value (`abs(b)` vs `a`) and boundary tests are authors' conventions | a recursive call is represented by its **parameter updates** (order-free under unification); base cases and input-only boundary guards are boundary, like loop initialisation |
| Q8 | copy propagation turned simultaneous updates `a := b % a, b := a` into `b := b % a` | substitution of a parameter / same-statement definition | never substitute parameters or definitions from the same statement |
| Q9 | iterative factorial marked trivial | gate counted only content relations | accumulator recurrences (`x = f(x, ...)`) and recursive computations (`n * f(...)`) qualify |
| Q10 | ternary returns attached the recursive call to the base case too | calls were collected from the whole statement | calls are collected per branch |
| Q11 | Haskell/Prolog tail calls were not results; their updates were separate statements | lowering asymmetry with `return f(...)` | a tail self-call is a `ret`; one recursive step = one statement (call + updates + result) in every lowerer |
| Q12 | Rust `if c { a } else { f(...) }` at the end of a function returned nothing | implicit return did not pass through `if` branches | implicit return propagates into branches |
| Q13 | `find_max_recursive` became "returns a recursive call" and matched merge sorts | the parameter updates sat on assignment statements, not on the return | a recursive return traces *all* parameter updates of its function; a bare `$self` return carries no content |
| Q14 | `get_prime` qualified through `x += 1` alone | a counter was taken for a recurrence | `x = x ± c` is a counter, not a computation |
| Q15 | quicksort written with comprehensions and `[*a, p, *b]`, Haskell `++` and `filter` | functional list idioms had no canonical form | canonical `filter(s, cond)`, `map(s, v, cond)`, `concat([...])`; Haskell sections and lambdas applied |
| Q16 | nested helpers (`merge` inside `merge_sort`) were never learned | the scanner stopped at function definitions | nested functions are lowered as `outer.inner` |
| Q17 | a Lisp `defun` without a name node and other odd forms crashed a run | unexpected tree shapes | any lowering crash becomes an explicit per-file error; evaluation continues |

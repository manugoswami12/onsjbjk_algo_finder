# AP13 v2.1: corpus self-validation, variant generalization, library forms, Windows

Targets set by the user (15 October 2026), from the project rating table:

- **5–6:**
  - corpus self-validation;
  - generalisation of variants with `term_subsumer/3` (least general generalisation);
  - precision of about 90% or more on the held-out set.
- **7:**
  - common library and idiom forms per language;
  - recall of about 40% or more;
  - runs on Windows.

All numbers below are measured on the frozen held-out set: `benchmark/rosetta_truth.json`, Rosetta Code, written before the first v2 run. They are not tuned per file. Section 5 has the measurements. Section 6 states plainly what was **not** reached.

## 1. Requirements → design (established basis)
| # | Requirement | Design | Basis |
|---|---|---|---|
| H1 | A reference that matches unrelated code must never be used | `cli.py validate`: scan every corpus file against the catalog. A reference that matches functions of ≥ 3 *other* files in ≥ 2 *other* categories is marked `generic` and is never matched again. The reason (the files it matched) is stored | Leave-one-out self-validation; precision first |
| H2 | One algorithm written as several variants (pivot choice, index base) | `cli.py generalize`: for variant A (file X) and B (file Y) of one family (file-name tokens), keep the **greedy maximal core** of A that also holds in B, with integers abstracted (Plotkin least general generalisation over constants, as in `term_subsumer/3`). It is stored only if the core keeps ≥ 60% of A and passes the quality gate. Each pair gets a fixed inference budget (`call_with_inference_limit/3`) | Plotkin 1970; Metzger and Wen (variation reduction) |
| H3 | Library and idiom forms | (a) Library *folds* `reduce(op, xs, z)`, `sum`, `prod`, `product`, Haskell `foldl (*)` become the accumulator loop they stand for, so traced references match them. (b) Direct library calls (`math.gcd`, `sort`, `bisect`…) are reported separately as `LIBRARY: <algorithm>`, never as a traced match | Metzger and Wen canonical forms; separate reporting keeps traced precision honest |
| H4 | Sound tracing (precision) | Copy propagation only along **reaching definitions**. An operand redefined on a path from definition to use (text order, loop back edge, not an exclusive branch) blocks substitution | Aho, Sethi and Ullman, reaching definitions; SSA copy propagation |
| H5 | Sound prefilter | The operator/call prefilter must never drop a reference that `canon.pl` could match. Operator families rewritten by canonicalisation (compare, `shr`→`div`, `add`↔`sub` by index shift) are expanded | Index must over-approximate the matcher |
| H6 | Windows | Explicit UTF-8 on every pipe. Reference lists go in an `@file` (command-line length limit). `.cmd` runners. GitHub Actions on `windows-latest` and `ubuntu-latest` | — |

## 2. Pseudocode (only what is new in v2.1)
```python
def validate(corpus, store, min_files=3, min_categories=2):
    hits = {label: set() for label in store}
    for f in corpus_files(store):                     # parallel, one swipl each
        for label in leaf_matches(scan(f)): hits[label].add(f)
    for label, m in store.items():
        others = hits[label] - {m.source_path, m.also_source}
        cats = {top_dir(p) for p in others} - {top_dir(m.source_path)}
        m.quality = 'generic' if len(others) >= min_files and len(cats) >= min_categories else 'usable'

def generalize(corpus, store):
    for y in files:                                   # variant B lives in file y
        refs = [a for x in files if x != y and len(tokens(x) & tokens(y)) >= 2 for a in refs_of(x)]
        for a in refs:                                # Prolog gen_main, inference budget per a
            if a already matches y: continue
            core = []
            for r in a.rels:                          # greedy maximal core (order of the trace)
                if consistent(core + [r], y): core.append(r)
                elif consistent(core + [abstract_ints(r)], y): core.append(abstract_ints(r))
            if len(core) >= 0.6 * len(a.rels) and len(core) < len(a.rels) and quality(core) == 'usable':
                store gen__a__hash(y) = core          # also_source = y
# consistent = one binding for all relations AND distinct program names (the leaf test)

def expand_folds(facts):                              # fact_io.FactSet.finish, every language
    for stmt S with a value containing reduce(op, xs, z) | sum(xs) | prod(xs) | product(xs):
        acc = z; loop L over xs with element e; acc = acc (op) e; replace the call by acc

def resolve(F, S, X):                                 # canon.pl copy propagation
    D = the single definition X := V0
    if no operand of V0 is killed on a path D -> S: substitute V0
    # kill: assignment / loop variable / element write or swap on a read sequence,
    # between D and S in text order or in a loop around S that does not re-run D,
    # and not in a branch exclusive with S
```

## 3. Activities and programs
| Type | Program | v2.1 change |
|---|---|---|
| User input (commands) | `tools/cli.py` | `validate`, `generalize`; `learn-dir` runs in parallel with one writer thread |
| Logic | `prolog/main.pl` | `gen_main`, `bounded_gen`, `greedy_core`, `consistent`, `abstract_ints` |
| Logic | `prolog/canon.pl` | `killed/4` (reaching definitions), `counting_range/1`, normalised values |
| Transform (shared) | `tools/fact_io.py` | `expand_folds`; parameter updates for every self-call |
| Transform | `lower_imperative.py`, `lower_equations.py`, `lower_prolog.pl` | R comma nodes; `tail(var(L), k)` for `a[k:]`, `a[k..]`, `x:xs`, `[H|T]`; operator sections |
| Static data | `tools/lang_tables.py` | `CALL_FOLDS`, `OPERATOR_FUNCTIONS`, `LIBRARY` |
| Knowledge store | `tools/knowledge_store.py` | prefilter families; `quality='generic'`, `also_source`, `corpus_matches` |
| Evaluation | `tools/rosetta_eval.py` | library metrics; precision and recall lines |

## 4. Problems found while measuring v2.1 (critical logic marked ★)
A row is critical when the logic interfaces with another program or is the base for more than two others.

| # | Observation | Cause | General fix |
|---|---|---|---|
| R1 ★ | Corpus insertion sort was learned as `a[i] = a[i]` | copy propagation substituted `key = a[i]` across the shifting loop that rewrites `a` and `i` | reaching-definition check (H4) |
| R2 | After R1, Python binary search lost its midpoint | text-order kill counted `low = mid + 1` against `high = mid - 1`, which is in the other branch, and counted a statement's own write against its read | exclusive guards are not paths; a statement reads before it writes |
| R3 ★ | C and Rust bubble sorts were never compared with the bubble reference | the prefilter required `add`, but the candidate had only `sub`; the index shift (`swap(i-1,i)` → `swap(j,j+1)`) rewrites one into the other | prefilter operator families (H5) |
| R4 | Every R call carried extra arguments | the R grammar names its `comma` separators | skip them in `args()` |
| R5 | `reduce(mul, range(1, n+1), 1)`, `prod(range(..))`, Haskell `product [1..n]` were opaque | library folds had no traced form outside Haskell `foldl` | `expand_folds` in the shared post-pass (H3a) |
| R6 | the expanded fold iterated `elem(range(..), e)` while loops iterate the counter | element iteration applied to ranges | an element of `range` / `seq_len` is the counter |
| R7 | Haskell `foldl (*) 1 xs` gave `call('(*)', …)` | operator sections applied directly were not operators | `(op) a b` is `a op b` |
| R8 | Haskell `n * factorial (n-1)` did not match recursive factorial | the equational lowerer added parameter updates only for tail calls | every self-call carries its parameter updates |
| R9 | Python `xs[1:]` vs Haskell `x:xs` vs Prolog `[H|T]` | slices were opaque; the tail was written with a bare atom, which is never variabilised | one term `tail(var(L), k)` |
| R10 | `<` in a Python filter vs `>=` in Haskell | assigned values were not given the comparison-direction normal form | `deep_norm` for values too |
| R11 ★ | `generalize` stalled: 120 s timeouts per file | conjunction matching is backtracking search; large pairs explode | per-reference inference budget; exceeding it means "no generalisation", never a guess |
| R12 | generalised cores could hold only with two names bound to one program variable | the core test was weaker than the leaf test | the core test is the leaf test (distinct names) |
| R13 | parameter-update de-duplication crashed on 37 corpus files | Python tuples holding lists are unhashable | key by the rendered term; regression test |
| R14 | some held-out "positive" files contain no algorithm (usage lines such as `(bubble-sort (list 5 4 3 2 1))`, imports only) | Rosetta pages split one solution over several files | kept in the frozen denominator; they count as misses, honestly |
| R15 | Lisp `(funcall compare a b)` with a passed-in predicate | the comparison direction is unknown statically | stays UNKNOWN (correct behaviour) |
| R16 ★ | `validate` marked the real factorial references generic | factorial is *reused* in many corpus files; "matches ≥ 3 other files" took reuse for genericness | only **one-way** matches count: if the matched function's own reference matches back, the two are the same algorithm (equivalence under subsumption) |
| R17 | re-validation un-marked generic references | generic references were not scanned, so they had no hits | validation scans `usable` and `generic` |
| R18 | `get_prime` (a pure counter `x += 1` twice) passed the gate | counter updates counted as content | `x = x ± c` is not a content relation |
| R19 ★ | `op(unknown, …)` unified with every other unknown operator (`parity` matched a binary gcd) | augmented operators missing from the table fell back to one shared atom | `^` `<<` `**` and augmented forms added; `^` is xor in C-family languages and power in Haskell and R; an unknown operator keeps its own spelling |
| R20 | `x = a + b` vs `x = b + a` | matching was not commutative | while **matching** (never while learning), the operands of commutative operators unify in either order, two outer levels (≤ 8 variants) |
| R21 ★ | cocktail sort and LCM identified as bubble sort and GCD | a reference that explains *part* of a function was taken as its identity | GRASPR cover: MATCH only if every effect of the involved functions is explained; otherwise `LEAF CONTAINS`. Bare recursive returns and delegations are plumbing |
| R22 ★ | every generalised reference matched with unbound names (235 evaluation errors) | `core_names` used `findall/3`, which copies variables | names collected from `term_variables/2` |
| R23 | a generalised core contained `cret(_, var(call('$self', _)))` | `quality/2` was called on the non-ground core and bound it | quality judged on a `numbervars` copy |
| R24 | greedy core dropped the exchange logic | a bare `return a` bound the name the exchange needed | informative relations first (effects, values, conditions, nesting, bare returns last) |
| R25 ★ | after generalisation, real bubble sorts were "odd-even sort" | a core reduced to a bubble pass still carried odd_even_sort's identity | ILP rule: a generalisation covers its two variant files and **no negative** — any match in another corpus file makes it generic |
| R26 | Fibonacci files identified as Lucas numbers | one recurrence, different seeds; initialisation was outside every trace | `seed(var(X), int(K))` for true recurrences (X reaches itself through the traced values), from constant initialisation or the wrapper call `step(0, 1, n)`; counters, offsets (`low = mid + 1`) and subscripts never get seeds |
| R27 | 12 held-out Prolog files failed completely | one clause with a dialect operator or a fragment aborted `read_term` | the clause is skipped and reported as `unsupported(…, 'syntax error …', Line)`; the rest of the file is lowered |
| R28 | `generalize` and `learn-dir` were slow (120 s timeouts; 16 min) | sequential and unbounded | per-reference inference budget; `learn-dir` traces files in parallel with one SQLite writer (64 s for 1,608 files) |

## 5. Measured results
(filled in from the runs below; commands in section 7)

## 6. What was not reached, and why

## 7. How to reproduce
```
python tools/cli.py --store S learn-dir  <TheAlgorithms/Python at e1a2a8b0>
python tools/cli.py --store S validate   <same corpus>
python tools/cli.py --store S generalize <same corpus>   # then validate again
python tools/rosetta_eval.py --store S [--no-fetch --rosetta <RosettaCodeData sparse clone>]
```
Windows: the same commands in the `ons_ruleskg` env with `A:\swipl\bin` on PATH; see `RUN_AP13*.cmd`.

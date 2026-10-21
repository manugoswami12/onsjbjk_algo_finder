# AP13 Requirements and Design: multi-language logic tracing (15 October 2026)

## 1. User objective
If the system learns from Python what an algorithm is (for example "bubble sort"),
it must use that knowledge on Rust, Java, C, R, Haskell, Common Lisp and Prolog
source code as well.

The critical step is **tracing the program's logic**: what is compared, what is
written where, which comparison controls which write, and which loop or
recursion carries the work. The **traced logic is then matched in SWI-Prolog**.

## 2. Why the existing tools cannot do it
| Component | Language dependence |
|---|---|
| AP9/AP10 `reference_pattern.py`, `ap10_threads.pl` | Exact Semgrep AST trees of *Python syntax* (tuple swap, `range`, `FloorDiv`) |
| AP11 `ingest.py` | Stores those trees, `language='Python'` |
| AP12 fallback `static_trace.py`, `interval_evidence.py` | Uses Python's `ast` module |

A Rust `v.swap(j, j+1)`, a C temporary-variable swap or a Haskell
`x:y:rest` guard therefore never matches anything learned from Python.

## 3. Non-negotiable constraints
- AP13 is a new folder, `polyglot_logic/`. No AP2-AP12 file is edited, deleted
  or replaced. AP12's `route_extended.pl` is *loaded* unchanged.
- Everything is deterministic. There is no ML, no LLM and no Popper; the user
  decided this because Popper is opaque and needs all-or-nothing direction
  declarations.
- Matching is never loosened. More syntactic variation selects a broader
  Prolog branch; it does not relax a leaf.
- Every result is `MATCH`, `PARTIAL` or `UNKNOWN`. `PARTIAL` must say which
  relation is missing. `UNKNOWN` is never converted into success.
- Labels are candidates. They are never proof of correctness or semantic
  equivalence.
- Candidate code is not executed. The only exception is the explicit, opt-in,
  sandboxed `check` command.
- Keep it simple. Use the Python standard library first, plus only:
  `tree-sitter-language-pack` (pip, MIT) and the existing SWI-Prolog.
- Windows CMD runners must use the user's portable `A:\swipl\bin` setup.

## 4. Established work adopted (not invented here)
| Need | Adopted practice | Where it is used |
|---|---|---|
| Parse 7 languages | tree-sitter-language-pack | `tools/parse_source.py` |
| Parse Prolog | SWI-Prolog's own `read_term/3` | `prolog/lower_prolog.pl` |
| Code as logic facts | JTransformer / SOUL / Glean / CodeQL: program elements as Datalog/Prolog facts | `tools/fact_io.py` |
| Logic tracing | Program Dependence Graph (Ferrante, Ottenstein & Warren 1987) and slicing (Weiser 1984); calls handled as in the SDG (Horwitz, Reps & Binkley 1990) | `prolog/slice.pl` |
| Reduce syntactic variation | Metzger & Wen 2000: canonical form before matching | `prolog/canon.pl` |
| Recognise algorithms | GRASPR cliche library (Wills 1992); IDL constraints with shared variables (Ginsbach et al. 2018); roles of variables (Taherkhani 2010) | `prolog/evidence.pl`, `prolog/leaf.pl` |
| Hierarchical routing | The validated AP12 `route_extended.pl` (11/11 live) | loaded unchanged |
| Generalise several references | Plotkin's least general generalisation, built into SWI-Prolog as `term_subsumer/3` | `prolog/learn.pl` |
| Haskell operator precedence | Dijkstra's shunting-yard, using the Haskell 2010 Report fixities | `tools/lower_equations.py` |
| Opt-in confirmation | Input/output agreement, after Stolee's Satsy | `tools/io_check.py` |

Deferred, with the reasons recorded in doc 02:

- LLVM `opt`, Soot/Jimple, GHC Core, GraalVM, Hat, Joern, CodeQL, Glean.
- Popper and ML embeddings, which are rejected.

## 5. Architecture
```
any of 8 languages
   │  tree-sitter (7 languages)  /  SWI read_term (Prolog)
   ▼
lowering table (data, lang_tables.py)  ──►  BASE FACTS (.pl): func, param, stmt, loop,
   in_loop, loop_var, loop_cond, guard, assign, par_assign, call_at, ret, next_stmt
   ▼  canon.pl  (swap idioms, loop forms, comparison direction, recursion = loop)
CANONICAL RELATIONS: exchange/5, under/2, cmp/4 ...
   ▼  slice.pl  (backward from outputs: returns and writes to parameters)
   ▼  evidence.pl
observed(F, Fact, Line)   ◄── same vocabulary as AP12 fallback
   ▼  UNCHANGED algo_reference_corpus/ap12/prolog/route_extended.pl
BRANCH: sequence_rearrangement / comparison_driven_reordering / indexed_lookup /
        interval_lookup / unknown
   ▼  leaf.pl: references learned for that branch only (all of them, no 100 cap)
MATCH label + bindings  |  PARTIAL label + missing relations  |  UNKNOWN
```
The learning path runs the same pipeline on Python references (one file, or
the AP11 corpus read-only). It slices them and writes one variabilised Prolog
clause per reference.

## 6. Language-neutral base facts
Every fact names its function `F` and statement `S`. `S` carries a source line.

| Fact | Meaning |
|---|---|
| `func(F, Name, Line)` | function or method, qualified name `Class.method` when nested |
| `param(F, K, Name)` | K-th parameter |
| `stmt(S, F, Kind, Line)` | statement; Kind ∈ assign, par_assign, call, ret, loop, other |
| `loop(L, F, Kind)` | Kind ∈ count, cond, recursion |
| `in_loop(S, L)` | S is (directly or not) inside loop L, same function |
| `loop_var(L, V)` | induction variable of a counting loop; `'$cursor'` for list recursion |
| `loop_cond(L, Cond)` | continuation condition |
| `guard(S, Cond, Pol)` | S runs only when Cond has polarity Pol (true/false) |
| `assign(S, Target, Value)` | Target = `var(N)` or `elem(Seq, Idx)` |
| `par_assign(S, Targets, Values)` | simultaneous assignment |
| `call_at(S, Name, Args)` | call inside statement S |
| `ret(S, Value)` | returned value |
| `next_stmt(S1, S2)` | S2 directly follows S1 in one block |
| `unsupported(F, What, Line)` | construct not modelled; shown in the report |

Expression terms are `var(N)`, `int(N)`, `op(Name, Args)`, `elem(Seq, Idx)`,
`call(Name, Args)` and `other(Kind)`. Operator names are normalised by the
tables: `//`, `%/%`, `div`, `floor` and integer `/` all become `div`.

## 7. Functional languages (Haskell, Prolog)
- All equations or clauses of one name form one function. If the function
  calls itself, that is a `recursion` loop.
- A guard (`| c`) and the body goals before `->` or `!` become `guard/3`.
  Each later alternative is guarded by the negation of the earlier ones.
- A recursive call's arguments are parameter updates:
  `go (mid+1) high` gives `assign(var(low), mid+1)`.
- A list pattern `x:y:rest` or `[X,Y|T]` binds `x = elem(L, cursor)` and
  `y = elem(L, cursor+1)`. The emitted output `y : f (x:rest)` or `[Y|R]`
  becomes a positional parallel assignment. For example, the
  Haskell/Prolog bubble pass produces the same `exchange` as the Python
  tuple swap.
- Single-assignment names (`where`, `let`, `X is E`, `nth0/3`) are substituted
  by their defining expression.

## 8. Learning (deterministic)
1. Run the pipeline on a Python reference function.
2. Slice it. Keep only:
   - the effects: writes and exchanges on parameters, and returns of
     non-constant values;
   - their guards;
   - their enclosing loops and the loop variables used;
   - definitions inside the same loop that the effects use.

   Docstrings, input validation and initialisation drop out automatically.
   This fixes the over-specific AP11 references.
3. Turn local names into Prolog variables, AP9 style, with distinct bindings.
   Store the result as `reference(Label, Branch, Relations)`.
4. For several references with the same label, SWI `term_subsumer/3` gives
   their least general generalisation (optional, `learn --generalise`).
5. Store a row in a new SQLite catalog `polyglot_logic/store/polyglot.sqlite3`
   with qualified identity `path::Class.func`, which fixes AP11's `__init__`
   collision. The `review_status` workflow is the same as AP11's.

## 9. Acceptance criteria (frozen before coding)
| Id | Test | Required result |
|---|---|---|
| A1 | the 11 AP12 fallback-POC Python examples via tree-sitter | same routes as the POC's expected set |
| A2 | bubble sort in 8 languages (`examples/bubble/`) | `comparison_driven_reordering`, plus leaf `MATCH` of the reference learned from `bubble.py` |
| A3 | binary search in 8 languages (`examples/binary_search/`) | `interval_lookup`, plus leaf `MATCH` of the reference learned from `binary_search.py` |
| A4 | negatives (`examples/negative/`): dead swap, wrong exchange, linear search, sum list, unrelated compare | no bubble or binary-search `MATCH`; routes no stronger than their evidence |
| A5 | mixed function (sort, then search) | both branches and both leaves |
| A6 | learning from AP11 store rows (fixture store) | patterns stored, qualified identity, rerun idempotent |
| A7 | missing tool (swipl, tree-sitter) | explicit error with exit code 2, never UNKNOWN-as-success |
| A8 | existing suites | unchanged results; `git diff` shows no frozen file changed |

## 10. Out of scope
- Proving that a program sorts or that two programs are equivalent.
- Aliasing analysis: an alias makes the result UNKNOWN.
- Higher-order library calls (`sorted`, `qsort`) as algorithm bodies.
- Exceptions, concurrency and macros other than the listed Lisp forms.

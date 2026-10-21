# AP13 v4: Prolog as the intermediate language — logic trace first, input→output as fallback (16 Oct 2026)

## 1. Requirement (user, 16 Oct)
> "trace logic, structure will always confuse you. if you can trace logic via prolog then you can do it …
> the intermediate language is prolog itself so you have to normalize each code to prolog.
> also input output is the fallback mechanism"

**What v1–v3.1 did wrong.** They compared *structure*: relation shapes and family rules over static facts. Every new variant needed a new canonical form or a new rule. The four recall failures of doc 09 §9 all come from this:
- Binet's Fibonacci;
- library-only files;
- Haskell combinators and `where` blocks;
- shape answers.

**v4:**
1. **Normalize** every function of every language into an **executable Prolog program** (the Prolog normal form, PNF).
2. **Trace the logic** by running the PNF on generated inputs, inside SWI-Prolog with an inference limit. The trace is the sequence of logic events on the inputs: comparisons of input elements, exchanges, element writes, appends, recursive calls and the result.
3. **Identify the algorithm** by trace equality with a learned reference on the same inputs.
4. **Fallback: input→output.** If no trace matches, the same outputs on all generated inputs mean the same *function* (the task). For example, Binet's Fibonacci = iterative Fibonacci, and any correct sort = `sorted`.
5. A program with nothing to run (an import, a transcript) is reported as such, with no claim.

## 2. Constraints
- The source program is **never executed in its own language**. Only its Prolog translation runs, inside a sandboxed interpreter:
  - no file, network or OS access;
  - printing is recorded, not performed;
  - `call_with_inference_limit/3` bounds every run.
- Working code is not changed. The new normalizer **subclasses** the existing `lower_imperative.Lowerer`: it reuses its `SPEC` tables and its `kind`, `role`, `expr`, `params` and `ternary` methods, and overrides only statement lowering, to produce structured PNF instead of flat facts.
- Deterministic: inputs are generated from a fixed seed.

## 3. Established basis
| Source | Used for |
|---|---|
| Horn clauses / Prolog as the analysis IR: Gange, Navas, Schachte, Søndergaard, Stuckey (TPLP 2015); CiaoPP; SeaHorn (LLVM→CHC), JayHorn (Java→CHC), RustHorn | every language → one Prolog normal form; loops as recursive predicates over explicit state |
| Definitional interpreters (Reynolds 1972); abstract machines in Prolog (Warren) | `interp.pl`: an operational semantics of the PNF written in Prolog |
| Dynamic dependence / trace-based recognition: DyCLINK (Su et al., FSE 2016), trace equivalence | algorithm identity = equal logic traces on equal inputs |
| Behavioural (I/O) equivalence by differential testing: Satsy (Stolee et al.), QuickCheck-style generated inputs (Claessen and Hughes 2000) | the fallback: function identity = equal outputs on a deterministic input battery |
| AP12 / AP13 dependence facts (this repo) | kept; the PNF is an *additional* view |

## 4. Prolog normal form (PNF)
```prolog
pnf_fun(Name, [Param...], Body).          % one per function, any language
% statements
seq([S...]) | assign(Target, Expr) | par_assign([T...], [E...]) | if(C, Then, Else)
| while(C, Body) | for_range(Var, From, To, Step, Body) | for_each(Var, Expr, Body)
| return(E) | break | continue | expr(E) | skip
% expressions: the existing lowerer terms
var(X) | int(N) | bool(B) | op(Op, [A, B]) | elem(Q, I) | call(F, Args) | list([...])
| tuple([...]) | cond(C, A, B) | filter(...) | map(...) | concat([...]) | tail(Q, K)
```
**Semantics (`interp.pl`):**
- environment = variable → value; sequences live in a heap (reference semantics), so in-place sorts and helper functions mutate the same list;
- Python index rules (negative indices, slices);
- integer division per language as in `lang_tables.INT_SLASH`.

## 5. Pseudocode
```python
def normal_form(source):                         # tools/to_prolog.py
    lang, tree = parse(source)
    if lang == 'prolog': return source_clauses   # already Prolog: run natively, sandboxed
    return PNFLowerer(lang).run(tree)            # subclass of lower_imperative.Lowerer

def run(pnf, fun, inputs):                       # prolog/interp.pl via env_run.swipl
    for x in inputs:
        out, trace = exec(fun, x, limit=10**6)   # trace = [cmp(i,j), swap(i,j), write(i,v), ret(v), ...]
    return outputs, traces

def inputs_for(fun):                             # tools/io_trace.py
    kinds = param_kinds(fun)                     # list-like / integer, from the PNF (elem, len, loops)
    return fixed_battery(kinds, seed=13)         # e.g. n in 0..15; lists of length 0..8

def identify(candidate):
    for ref in references_with_same_kinds(candidate):
        if traces(candidate) == traces(ref):     return IDENTIFIED(ref)     # same logic
    for ref in ...:
        if outputs(candidate) == outputs(ref):   return SAME_FUNCTION(ref)  # fallback: same I/O
    return UNKNOWN(reason)
```

## 6. Activities and programs
| Type | Program |
|---|---|
| Transform: language → PNF | `tools/to_prolog.py` (subclass of `lower_imperative.Lowerer`) |
| Logic: interpreter, tracing, builtins | `prolog/interp.pl` |
| Environment: runs | `prolog/run_main.pl` via `env_run.swipl` (unchanged) |
| Input battery and comparison | `tools/io_trace.py` |
| Own cases | `examples/v4/` with expectations frozen first |
| Evaluation | `tools/io_eval.py` (dev/test split as in doc 08) |

## 7. Critical logic
| Logic | Why critical | Risk | Safeguard |
|---|---|---|---|
| PNF translation | the base for everything | a mistranslation makes a wrong program "equal" | a translated program must reproduce known outputs on own cases; untranslatable statements make the function UNRUNNABLE, never silently skipped |
| interpreter semantics (heap, indices, division) | interfaces with every language | the same source meaning differs by language (`/`, `%` on negatives) | per-language operator table (existing `lang_tables`) |
| input battery | decides equivalence | too few inputs make different functions look equal | ≥ 12 inputs incl. edge cases (0, 1, empty, sorted, reverse, duplicates); a claim needs ALL equal |
| trace equality | algorithm identity | traces that differ only by the order of independent events | events on input positions only; the same tie-breaking inputs |
| inference limit | the sandbox | non-termination | `call_with_inference_limit/3`; exceeding it gives `timeout`, never a guess |

## 8. Problems
To be filled while building (as in docs 05, 07, 08, 09).

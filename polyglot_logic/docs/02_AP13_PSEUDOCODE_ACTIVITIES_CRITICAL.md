# AP13 Pseudocode, Activity Classification and Critical Logic

## 1. Requirements → pseudocode (Python-style)

### R1. Read and parse any supported source (`parse_source.py`)
```python
def parse(path):
    lang = EXTENSION_TO_LANGUAGE[path.suffix.lower()]  # .py .rs .java .c .h .R .hs .lisp .lsp .cl .pl .pro
    if lang is None:
        exit(2, 'unsupported language')
    if lang == 'prolog':
        return lang, None                     # SWI read_term parses it later (R3d)
    source = path.read_bytes()                # never imported, never executed
    if len(source) > 1_000_000:
        exit(2, 'too large')
    parser = tree_sitter_language_pack.get_parser(lang)   # missing package -> exit 2
    tree = parser.parse(source)
    if tree.root_node.has_error:
        record_limitation('parse error, partial facts')
    return lang, tree.root_node
```

### R2. One table of language data (`lang_tables.py`)
```python
EXTENSION_TO_LANGUAGE = {...}
OPERATORS = {'>': 'gt', '<': 'lt', '>=': 'ge', '<=': 'le', '==': 'eq', '!=': 'ne',
             '=:=': 'eq', '=\\=': 'ne', '/=': 'ne', '=<': 'le', '=': 'eq',
             '+': 'add', '-': 'sub', '*': 'mul', '//': 'div', '%/%': 'div',
             'div': 'div', 'quot': 'div', '%': 'mod', 'mod': 'mod', ...}
INT_DIVISION_SLASH = {'c', 'java', 'rust'}    # '/' on integers means div
SPEC[lang] = {node_type: (kind, {role: field_or_child_index})}
#  kinds: function, block, for_range, c_for, while, if, assign, aug_assign,
#         decl, return, expr_stmt, binary, compare, unary, paren, index,
#         ident, int, bool, call, method_call, field, cast, tuple
HASKELL_FIXITY = {'!': ('l', 9), '*': ('l', 7), 'div': ('l', 7), '+': ('l', 6),
                  '-': ('l', 6), ':': ('r', 5), '==': ('n', 4), '<': ('n', 4), ...}
LISP_FORMS = {'defun', 'let', 'let*', 'dotimes', 'loop', 'when', 'unless', 'if',
              'cond', 'setf', 'setq', 'incf', 'decf', 'rotatef', 'return-from',
              'return', 'progn', 'aref', 'floor', 'length', '1+', '1-', ...}
```

### R3a. Imperative lowering (Python, Rust, Java, C, R) (`lower_imperative.py`)
```python
def lower(lang, root):
    facts = FactSet()
    for fn_node, qualified in find_functions(root, SPEC[lang]):   # Class.method
        F = facts.new_func(qualified, line(fn_node))
        for k, name in enumerate(param_names(fn_node)):
            facts.add('param', F, k, name)
        walk_block(body(fn_node), Ctx(F, loops=[], guards=[]), facts, last_is_return=True)
    return facts

def walk_stmt(node, ctx):
    kind, roles = SPEC.lookup(node.type)
    if kind == 'block':
        prev = None
        for child in statements(node):
            s = walk_stmt(child, ctx)
            if prev and s:
                add('next_stmt', prev, s)
            prev = s
    elif kind in ('for_range', 'c_for', 'while'):
        L = new_stmt(ctx, 'loop', node)
        add('loop', L, ctx.F, 'count' if kind != 'while' else 'cond')
        if kind == 'for_range':
            add('loop_var', L, name(role(node, 'var')))
        if kind == 'c_for':
            walk_stmt(role('init'))
            add('loop_var', L, updated_name(role('update')))
            add('loop_cond', L, expr(role('cond')))
        if kind == 'while':
            add('loop_cond', L, expr(role('cond')))
        walk_block(role('body'), ctx.with_loop(L))
    elif kind == 'if':                     # also elif chains / else-if / R / Rust
        cond = expr(role('cond'))
        if cond == bool(False):
            walk(else part only)           # statically dead branch skipped (AP12 rule)
        else:
            walk_block(role('then'), ctx.with_guard(cond, True))
            for alt in alternatives(node):  # elif keeps accumulating negations
                walk(alt, ctx.with_guard(cond, False))
    elif kind in ('assign', 'decl', 'aug_assign'):
        S = new_stmt(ctx, 'assign', node)
        lhs, rhs = role('left'), role('right')
        if is_tuple(lhs):
            add('par_assign', S, [expr(x) for x in lhs], [expr(x) for x in rhs])
        else:
            value = op(aug_op, [expr(lhs), expr(rhs)]) if kind == 'aug_assign' else expr(rhs)
            add('assign', S, expr(lhs), value)
    elif kind == 'return' or (last statement of function and is expression):
        S = new_stmt(ctx, 'ret', node)
        add('ret', S, expr(value))
    elif kind == 'expr_stmt':
        walk_expression_statement(...)      # call -> stmt 'call'; assignment expression -> assign
    else:
        S = new_stmt(ctx, 'other', node)
    for call in calls_inside(node):         # every call, for interprocedural nesting
        add('call_at', S, call.name, call.args)

def new_stmt(ctx, kind, node):
    S = next_id('s')
    add('stmt', S, ctx.F, kind, line(node))
    for L in ctx.loops:
        add('in_loop', S, L)
    for (c, polarity) in ctx.guards:
        add('guard', S, c, polarity)
    return S

def expr(node):                     # -> Prolog term
    match SPEC.kind(node):
        'ident'      -> var(name)
        'int'        -> int(value)  # R '1' float literal -> int(1) when integral
        'bool'       -> bool(true/false)
        'paren'|'cast' -> expr(inner)
        'index'      -> elem(expr(seq), expr(index))
        'binary'|'compare' -> op(OPERATORS[text], [expr(l), expr(r)])  # '/' -> div for C/Java/Rust
        'unary' '-'  -> int(-n) or op(neg, [x])
        'call'       -> call(name, args)        # return(x) in R becomes ret
        'method_call'-> call(method, [receiver] + args)   # v.swap(i, j) -> call(swap, [v, i, j])
        'field' .length / .len() -> call(len, [obj])
        other        -> other(node.type)
    then normalise: add(int, X) -> add(X, int); add(X, int(0)) -> X
```

### R3b. S-expression lowering (Common Lisp) (`lower_sexpr.py`)
```python
def lower(root):
    for form in to_lists(root):                   # tree-sitter -> nested Python lists
        if head(form) == 'defun':
            F = new_func(name)
            params(form[2])
            body_forms(form[3:], ctx, implicit_return=True)

def form_stmt(f, ctx):
    head = f[0]
    if head in ('let', 'let*'):     assign each binding; body_forms(rest)
    elif head == 'dotimes':         L = loop(count); loop_var(v); body under L
    elif head == 'loop' and 'while' in f:  L = loop(cond); loop_cond; body after 'do'
    elif head in ('when', 'unless', 'if'):  guards like R3a
    elif head == 'cond':            chain clauses, accumulating negations; 't' = else
    elif head in ('setf', 'setq'):  assign pairs
    elif head in ('incf', 'decf'):  assign(place, op(add|sub, [place, n]))
    elif head == 'rotatef':         par_assign([a, b], [b, a])
    elif head in ('return-from', 'return'):  ret(value)
    else:                           call / other

def sexpr(x):
    (op a b ...)     -> left-folded op(name, [...])    (> a b) -> op(gt, [a, b])
    (aref a i)       -> elem(a, i)
    (1+ x)           -> op(add, [x, int(1)])
    (floor (+ a b) 2) -> op(div, [op(add, [a, b]), int(2)])
    (length a)       -> call(len, [a])
```

### R3c. Equation lowering (Haskell) (`lower_equations.py`)
```python
def lower(root):
    groups = group_equations_by_name(top-level + where/let local_binds)
    for name, equations in groups:
        if every equation has no patterns and is not recursive:
            continue                          # plain value binding -> assigned where used
        F = new_func(name)
        params = names from first variable patterns, else '$arg<k>'
        recursive = any(apply(head == name) in equations)
        L = new_loop(F, 'recursion') if recursive else None
        previous_guards = []
        for eq in equations:
            env, guards = bind_patterns(eq.patterns, params)
            #  x:y:rest on param p  -> env[x] = elem(var(p), var('$cursor'))
            #                         env[y] = elem(var(p), op(add, [var('$cursor'), int(1)]))
            #                         env[rest] = tail(p); loop_var(L, '$cursor')
            #  literal 0 on param p -> guard op(eq, [var(p), int(0)])
            #  variable v on param p -> env[v] = var(p)
            for local in eq.where_binds:
                stmt assign(var(local), expr(rhs, env))
            for alternative in eq.guarded_bodies:         # | g = e   chains
                g = expr(alternative.guard, env)          # 'otherwise' -> no guard
                lower_result(alternative.body, env, guards + negated(previous alternatives) + [g])
            if eq has refutable patterns:
                previous_guards.append(pattern guard)     # later equations do not see it
        if recursive:
            loop_cond(L, negation of base-case guard over two parameters), when one exists

def lower_result(e, env, guards):
    writes = []; updates = []
    while e is cons(h, t):                    # y : rest
        writes.append((elem(list, cursor + k), expr(h, env))); e = t
    if e is self-call(args):
        for k, a in enumerate(args):
            if a is cons(h, tail_of_param):   # recursion continues with x : rest
                writes.append((elem(list, cursor + 1), expr(h, env)))
            elif expr(a, env) != var(param k):
                updates.append(assign(var(param k), expr(a, env)))
        stmts: one par_assign(writes) (identity writes dropped), each update, call_at
    else:
        ret(expr(e, env))
expr(): infix chains are rebuilt with shunting-yard using HASKELL_FIXITY;
        apply chains -> call(name, args); `a ! i` -> elem(a, i); `x \`div\` y` -> op(div)
```

### R3d. Clause lowering (Prolog) (`prolog/lower_prolog.pl`, runs inside SWI)
```python
def lower_prolog(file):
    clauses = read_term(stream, T, variable_names(Vs), term_position(P))  # until EOF
    for (name, arity), cls in group(clauses):
        F = new_func(name/arity); params = first-clause head variable names or 'argK'
        recursive = any body goal is name/arity
        L = loop(F, recursion) if recursive
        prior_guards = []
        for clause in cls:
            env = substitution for head args (as R3c; [X,Y|T] = elem(list, $cursor + k))
            guards = negated(prior_guards that were followed by a cut)
            for goal in body (conjunction, left to right):
                comparison (>, <, >=, =<, =:=, =\=)   -> guard for the rest of the clause
                X is E                               -> assign(var(X), E)
                nth0(I, L, V) / nth1                 -> env[V] = elem(L, I)
                length(L, N)                         -> assign(var(N), call(len, [L]))
                (C -> A ; B)                         -> A under C/true, B under C/false (chains)
                Out = E   where Out is a head output var -> ret(E)
                recursive call                       -> parameter updates + positional writes (as R3c)
                other call                           -> call_at
                !                                    -> remember: this clause's guards exclude later clauses
            head output pattern [Y|R], R passed to the recursive call -> write elem(list, cursor) := Y
            head output constant (e.g. -1), base clause -> ret(constant)
```

### R4. Write and read fact files (`fact_io.py`)
```python
def write(facts, path):
    group clauses by predicate (no discontiguous warnings), header comment
    every atom quoted with export_ast_facts.atom()   # reused, never splice source as code
def term(x):                       # Python tuple tree -> safe Prolog text
```

### R5. Canonicalisation (`prolog/canon.pl`)
```python
exchange(S, Q, I, J) if
    par_assign(S, [elem(Q, I), elem(Q, J)], [elem(Q, J), elem(Q, I)]) and I != J
    or temp triple: t = Q[I]; Q[I] = Q[J]; Q[J] = t  (next_stmt chain)
    or call_at(S, swap, [Q, I, J])   (Rust v.swap, Java Collections.swap)
norm(op(lt, [A, B])) = op(gt, [B, A]); norm(op(le, [A, B])) = op(ge, [B, A])
norm(not(...)) pushes negation: not(gt(A, B)) = ge(B, A) ...
nguard(S, C', P) for every guard(S, C, P), C' = norm(C); eq is tried in both orders
value(S, Target, E): assign value with copy propagation of single-definition temporaries
canonical midpoint: op(add, [L, op(div, [op(sub, [H, L]), 2])]) == op(div, [op(add, [L, H]), 2])
under(X, L): in_loop(X, L); or X is in function G and a call to G occurs in a statement under L;
             loops nest the same way (transitive)
live(S): no guard with a constant-false condition
```

### R6. Logic tracing / slicing (`prolog/slice.pl`)
```python
def effects(F):            # outputs of the function
    exchanges in F; writes elem(param, _) in F; ret(S, V) under a loop with V not a constant
def slice(F):
    work = effects(F); rel = []
    for each effect S:
        rel += [effect relation, every nguard(S, C, P), under(S, L) for each loop L,
                nesting under(L1, L2) among those loops,
                loop_var(L, V) when V occurs in the effect/guards, loop_cond(L, C) for cond loops]
        for each variable X used (not param, not loop var):
            for definition D of X under one of S's loops:   # loop-carried data dependence
                rel += [value(D, var(X), E), under(D, L), nguard(D, ...)]; repeat for vars of E
    return rel                      # docstrings / validation / initialisation never reached
```

### R7. Evidence for the unchanged AP12 router (`prolog/evidence.pl`)
```python
evidence(F, returned_input, Line)            ret of a parameter
evidence(F, element_exchange, Line)          exchange on a parameter sequence
evidence(F, input_sequence_mutated, Line)    same exchange (AP12 semantics)
evidence(F, comparison_controls_exchange, Line)  true guard compares Q[I] with Q[J] of that exchange
evidence(F, indexed_equality_controls_index_return, Line)
        ret(var(M)) under a loop, true guard eq(elem(A, M), T), A and T distinct parameters
evidence(F, coherent_midpoint_interval_update, Line)
        cond loop ge(H, L) (= L <= H); M := midpoint(L, H); L := M + 1 guarded; H := M - 1 guarded
evidence(F, bounded_indexed_interval_lookup, Line)
        midpoint in a loop, comparison of A[M] with parameter T guards L := M + 1 and H := M or M - 1
then: assertz(program(F, anonymous)), assertz(observed(F, Fact, Line)); route(F, B) from route_extended.pl
```

### R8. Leaf matching (`prolog/leaf.pl`)
```python
for reference(Label, Branch, Relations) whose Branch is routed for some function, or Branch == unknown:
    if conjunction(Relations) holds with distinct local bindings:
        MATCH Label, functions involved, bindings
    else:
        missing      = [r for r in Relations if not exists(r)]   # relation absent entirely
        inconsistent = [] if missing else 'relations exist but not with one consistent binding'
        if fraction present >= 1/2: PARTIAL Label, missing / inconsistent   # diagnostic, never a match
```

### R9. Learn a reference (`prolog/learn.pl` + `knowledge_store.py`)
```python
def learn(label, source, function):
    facts = lower(source); rels = slice(function)   (in Prolog)
    if not rels: status = 'no_effects'  # recorded, not a pattern
    branch = most specific route of the function (interval_lookup > indexed_lookup >
             comparison_driven_reordering > sequence_rearrangement > unknown)
    clause = variabilise(rels)   # every name atom inside var(_) and every S/L id -> fresh Prolog variable
    write 'reference(Label, Branch, Rels).' with portray_clause -> store/patterns/<label>.pl
    sqlite insert (idempotent: same sha -> already_present; different -> integrity error)
def learn_corpus(ap11_store, corpus_root, categories, limit):
    open ap11 references.sqlite3 with sqlite URI mode=ro           # strictly read-only
    for row in generated rows of categories (stable order):
        path = ap11.source.source_path(corpus_root, row.relative_path)   # reused safety check
        for each function occurrence whose plain name == row.function_name:
            learn(label=f'{row.label}__{qualifier}', ...)   # qualified identity fixes __init__ collisions
    print counts: generated, no_effects, already_present, errors (never hidden)
def generalise(label_prefix):   # optional: term_subsumer/3 over references of one label family
```

### R10. Scan and report (`cli.py`, `report.py`)
```python
def scan(source, store):
    facts = lower(source); refs = all .pl patterns with review filter (default approved+unreviewed flag)
    out = swipl(main.pl, scan, facts, refs)       # one subprocess, timeout, stdin closed
    parse lines FUNC|ROUTE|OBS|UNSUP|LEAF; anything malformed -> error exit 2
    print per function: branches, evidence lines, leaf MATCH/PARTIAL, limitations
    print 'NOT A PROOF OF ALGORITHM IDENTITY OR CORRECTNESS'
```

### R11. Opt-in behaviour confirmation (`io_check.py`)
```python
def check(candidate, lang, function, kind in {sort, search}, reference_py, ref_function):
    inputs = deterministic seeded lists (empty, single, sorted, reversed, duplicates, random)
    expected = run reference in subprocess (python -I, temp dir, timeout)
    actual = run language harness template (compile/run in temp dir, timeout, no stdin)
    compare relationally: sort -> same list; search -> found index holds target, or both 'not found'
    print 'IO_AGREEMENT k/n' (evidence only)
```

## 2. Activity classification (requirements → pseudocode → type → one program)
| Type | Pseudocode steps | Program |
|---|---|---|
| Environment / external-program interface | find `swipl`, run with timeout, stdin closed, temp dirs; compilers for R11 | `tools/env_run.py` |
| Static data (tables) | R2 | `tools/lang_tables.py` |
| Source input / parse | R1 | `tools/parse_source.py` |
| Transform: imperative syntax | R3a | `tools/lower_imperative.py` |
| Transform: s-expressions | R3b | `tools/lower_sexpr.py` |
| Transform: equations | R3c | `tools/lower_equations.py` |
| Transform: Prolog clauses | R3d | `prolog/lower_prolog.pl` |
| File save / load (facts) | R4 | `tools/fact_io.py` |
| Logic (rules) | R5–R9 Prolog parts | `prolog/canon.pl`, `slice.pl`, `evidence.pl`, `leaf.pl`, `learn.pl`, `main.pl` |
| Knowledge storage (SQLite + .pl) | R9 storage, AP11 read-only | `tools/knowledge_store.py` |
| Display output | R10 printing | `tools/report.py` |
| User input (commands) | argparse: facts, scan, learn, learn-corpus, approve, status, check | `tools/cli.py`, `RUN_AP13*.cmd/.sh` |
| Execute-and-compare (opt-in) | R11 | `tools/io_check.py` |
| Evaluation (held-out benchmark) | fetch Rosetta Code (not committed), learn from Python examples, scan, count | `tools/rosetta_eval.py`, `RUN_AP13_ROSETTA.*` |

## 3. Critical logic
Logic is **critical** when it interfaces with the environment or another program,
or when more than two other parts depend on it.

| Critical logic | Why critical | Risk | Safeguard |
|---|---|---|---|
| tree-sitter interface (`parse_source`) | external library; grammars downloaded at first use | missing package or offline grammar → silent nothing | explicit exit 2 with install/prefetch hint; `has_error` reported |
| Lowering tables (`lang_tables`) | base of all 5 lowerers | wrong field name → silently lost statement | unknown node types become `other(...)`/`unsupported` facts, shown in report; golden-fact tests |
| Base-fact vocabulary | base of canon, slice, evidence, leaf, learn | two languages emitting different shapes for same logic | one vocabulary spec (doc 01 §6); 8-language parity tests |
| `canon.pl` | base of evidence, slice, leaf | over-eager rewrite creates false exchanges | only listed idioms; negative examples (identity swap, j/j+2 swap) in acceptance |
| `slice.pl` | base of learning and so of all leaf matches | slice too small (false matches) or too big (no generalisation) | slice keeps effects + guards + loops + loop-carried defs; tests on both families and negatives |
| SWI-Prolog subprocess (`env_run`) | other program | hang at toplevel, warnings mistaken for data | `-g main -t halt`, stdin DEVNULL, timeout, line protocol validated, stderr treated as failure |
| AP12 `route_extended.pl` reuse | other component, frozen | redefinition clash (`dynamic observed/3`) | loaded first; evidence asserted as facts; file never modified |
| AP11 SQLite read | other program's data | accidental write or lock | `sqlite3` URI `mode=ro`; path checks via `ap11.source.source_path` |
| Knowledge store writes | base of scan | duplicate/conflicting patterns | sha-256 per pattern; idempotent replay; conflict → error |
| `io_check` sandbox | executes code | runaway or harmful code | opt-in only, temp dir, timeout, no stdin, `python -I`; documented as not a security sandbox |

## 4. Problems faced and how each is handled
| # | Problem | Handling |
|---|---|---|
| P1 | tree-sitter-haskell parses `a ! mid == target` as a flat right-nested chain (no fixities) | flatten chain, rebuild with shunting-yard + Haskell Report fixities |
| P2 | Python `elif`/`else` are siblings with field `alternative` (several) | walk alternatives in order, accumulating negated guards |
| P3 | R numerals parse as `float` ('1'); R is 1-based | integral floats → `int`; initialisation is outside slices, so base index never matters |
| P4 | R assignment is `binary_operator <-`; function is `name <- function(...)` | table entries for `<-`, `=`, `->`; function found by rhs type |
| P5 | Rust/R/Haskell/Lisp return the last expression implicitly | last body expression lowered as `ret` |
| P6 | Rust `v[mid as usize]` casts | `cast` kind is transparent |
| P7 | Java `a.length`, Rust `v.len()`, Python `len(x)`, R `length(x)`, Lisp `(length a)` | all → `call(len, [x])` |
| P8 | Swap idioms differ (tuple, temp triple, `.swap`, `Collections.swap`, `rotatef`, functional rewrite) | all canonicalised to `exchange/4` in `canon.pl` |
| P9 | Haskell/Prolog have no loops, only recursion; outer loop is another function | recursion = loop; interprocedural `under/2` through `call_at` |
| P10 | Prolog cut and clause order act as guards | later clauses receive the negated guards of earlier cut clauses |
| P11 | Prolog output arguments (`Index = Mid`, `[Y|R]`) | head output variables → `ret` / positional writes |
| P12 | Lisp `loop` macro has many clause forms | only `loop while C do ...` modelled; others → `unsupported` |
| P13 | tree-sitter-language-pack downloads grammars at first use (office PC may be offline) | `RUN_AP13.cmd prefetch` runs `download([...8 langs])` once while online |
| P14 | Two `__init__` (or same-name) methods in one file | qualified identity `Class.method` |
| P15 | AP11 references contain docstrings / validation | slicing never reaches them |
| P16 | Scan limited to 100 references in AP11 | only references of the routed branch are loaded, all of them |
| P17 | `if False:` dead code (AP12 test) | constant-false guard ⇒ statement not live |
| P18 | Aliasing (`b = a`), higher-order calls, exceptions | not modelled; may give UNKNOWN (stated, never guessed) |
| P19 | Deferred tools: LLVM `opt` (C/Rust only, Windows toolchain), Soot (JVM jar), GHC Core (multi-GB GHC), GraalVM/Hat (heavy/unmaintained), Joern/CodeQL/Glean (no Haskell/R/Lisp/Prolog) | revisit only if the benchmark shows a language-specific gap |
| P20 | Popper rejected by the user (opaque, all-or-nothing directions) | deterministic slicing + `term_subsumer/3` |

Found while building and measuring (all fixed generally, none per file):

| # | Problem | Handling |
|---|---|---|
| P21 | SWI-Prolog 9.0.4 honours only one `-s` flag (also why AP10 runners fail in the container) | `env_run.swipl` loads all files with one quoted `load_files/2` goal |
| P22 | Learned pattern files redefine `reference/4` when consulted | patterns are *read* as terms; only `reference/4` facts accepted |
| P23 | `findall` copies variables, so the distinct-name check lost its binding | names collected without `findall` |
| P24 | `if a[m]==x: return m` then a separate `if` (no `elif`) | early-return control dependence: later statements guarded by `not c` |
| P25 | `swap(i-1, i)` versus `swap(j, j+1)` | per-statement induction-variable index shift |
| P26 | `> / elif < / else` never writes `==` | strict-total-order consequences derived in `nguard0/3` |
| P27 | Java `do…while`, R `repeat`, `compareTo`, `>>> 1`, R vector swap, `Some`/`Just` | table entries + canonical rules |
| P28 | Prolog 0-arity predicates (`numlist(1,0,_)` fails); nested `;` in bodies | arity 0 handled; unmodelled forms emit `unsupported/3` |
| P29 | Lisp forms with a computed head `((lambda ...) ...)` crashed the lowerer | treated as `other(computed_call)` |

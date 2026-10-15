/* AP13 logic tracing: backward slice from a function's outputs (Weiser 1984)
   over control dependences (guards, enclosing loops) and data dependences
   (loop-carried definitions), on the language-neutral canonical relations.
   The slice is a list of ground relations; docstrings, input validation and
   initialisation outside the loops are never reached (doc 01 section 8).
*/

% Effects (outputs) of F and of the functions it calls (doc 04 G1):
% exchanges, element writes, appends, and returned/yielded computed values.
effect(F, exchange(S, Q, I, J)) :-
    reaches(F, G), stmt(S, G, _, _), once(exchange(S, Q, I, J)).
effect(F, value(S, elem(Q, I), V)) :-
    reaches(F, G), stmt(S, G, _, _), value(S, elem(Q, I), V),
    \+ exchange(S, _, _, _), \+ temp_swap_part(S).
effect(F, capp(S, Q, X)) :-
    reaches(F, G), stmt(S, G, _, _), capp(S, Q, X).
effect(F, cret(S, V)) :-
    reaches(F, G), stmt(S, G, _, _), cret(S, V0), computed(G, V0),
    \+ base_case(G, S, V0), V = V0.

% In a recursive function a non-recursive return is the recursion's boundary
% (like loop initialisation): not core logic.
base_case(G, S, V) :- recursive(G), in_loop(S, L), loop(L, G, recursion), \+ sub_term(call('$self', _), V).
recursive(G) :- loop(_, G, recursion), !.

% boundary guard: compares only inputs/constants (n <= 1, a == 0); data guards stay
boundary_guard(S, C) :- in_loop(S, L), stmt(L, G, _, _), loop(L, G, recursion),
    \+ sub_term(elem(_, _), C).

% a returned value carries computation: not a constant, not the unchanged input,
% not a plain delegation to another function
computed(_, V) :- V = int(_), !, fail.
computed(_, V) :- V = bool(_), !, fail.
computed(_, V) :- V = other(_), !, fail.
computed(G, var(P)) :- untouched_input(G, P), !, fail.
% plain delegation: a non-recursive call whose arguments are only inputs/constants
computed(G, call(N, A)) :- N \== '$self', \+ sub_term(call('$self', _), A),
    forall(member(X, A), ( X = int(_) ; X = var(P), untouched_input(G, P) )), !, fail.
computed(_, _).

% a parameter the function never reassigns is just the input passed through
untouched_input(G, P) :-
    param(G, _, P),
    \+ ( assign(S, var(P), _), stmt_func(S, G) ),
    \+ ( par_assign(S, Ts, _), stmt_func(S, G), memberchk(var(P), Ts) ).

temp_swap_part(S) :- assign(S, var(T), elem(_, _)), next_stmt(S, S2), exchange(S2, _, _, _), T \== '$none'.
temp_swap_part(S) :- assign(S, elem(_, _), var(_)), next_stmt(S0, S), exchange(S0, _, _, _).

effect_stmt(exchange(S, _, _, _), S).
effect_stmt(value(S, _, _), S).
effect_stmt(capp(S, _, _), S).
effect_stmt(cret(S, _), S).

slice(F, Rels) :-
    findall(E, effect(F, E), Es0), sort(Es0, Es),
    Es \== [],
    once(( member(E0, Es), effect_stmt(E0, S0), stmt(S0, F, _, _) )),  % F computes itself;
                                                                     % pure wrappers are not learned
    foldl(effect_relations(F), Es, [], R0),
    reverse(R0, R1), list_to_set(R1, Rels).

effect_relations(F, E, Acc0, Acc) :-
    effect_stmt(E, S),
    findall(L, under(S, L), Ls0), sort(Ls0, Ls),
    stmt_relations(S, Ls, Ctl),
    findall(under(L1, L2), (member(L1, Ls), member(L2, Ls), L1 \== L2, under(L1, L2)), Nest),
    findall(lcond(L, C), (member(L, Ls), loop(L, _, K), K == cond, once(lcond(L, C))), Conds),
    findall(P, value(S, var(P), _), Updated0),      % parameter updates of a recursive call
    (   E = cret(_, RV), sub_term(call('$self', _), RV), stmt(S, G0, _, _)
    ->  findall(P, (param(G0, _, P), value(D, var(P), _), stmt(D, G0, _, _)), Up2)  % all updates of
    ;   Up2 = []                                                                     % the recursion
    ),
    append(Updated0, Up2, Updated),
    term_names([E|Ctl], Used0), append(Used0, Updated, Used1), sort(Used1, Used),
    findall(lvar(L, var(V)), (member(L, Ls), loop_var(L, V), memberchk(V, Used)), LVars),
    loop_names(Ls, LoopNames),
    findall(P, (reaches(F, G), untouched_input(G, P)), Inputs),
    findall(L2, (reaches(F, G), loop(L2, G, _)), AllLoops0), sort(AllLoops0, AllLoops),
    loop_names(AllLoops, AllLoopNames),
    append([LoopNames, AllLoopNames, Inputs], Known),
    data_deps(Used, AllLoops, Known, [], Deps),       % G3: definitions inside ANY loop
    append([[E], Ctl, Nest, Conds, LVars, Deps], New),
    reverse(New, RNew), append(RNew, Acc0, Acc).

% guards and enclosing loops of one statement (control dependence)
stmt_relations(S, Ls, Rels) :-
    findall(nguard(S, C, P), (first_nguard(S, C, P), \+ boundary_guard(S, C)), Gs),
    findall(under(S, L), member(L, Ls), Us),
    append(Gs, Us, Rels).

first_nguard(S, C, P) :-
    guard(S, C0, P0), C0 \= bool(_), norm_pol(C0, P0, C1, P),
    shift_term(S, C1, C2), elem_iter(S, C2, C).

loop_names(Ls, Names) :- findall(V, (member(L, Ls), loop_var(L, V)), Names).
inputs(F, Names) :- findall(P, (reaches(F, G), param(G, _, P)), Names).

% loop-carried data dependences: definitions inside the effect's loops
data_deps([], _, _, _, []).
data_deps([X|Xs], Ls, Known, Seen, Deps) :-
    (   ( memberchk(X, Known) ; memberchk(X, Seen) ; Ls == [] )
    ->  data_deps(Xs, Ls, Known, Seen, Deps)
    ;   findall(D-V, (value(D, var(X), V), member(L, Ls), under(D, L)), Defs0),
        sort(Defs0, Defs),
        findall(R, ( member(D-V, Defs),
                     ( R = value(D, var(X), V)
                     ; member(L, Ls), under(D, L), R = under(D, L)
                     ; member(L, Ls), under(D, L), loop_var(L, LV),
                       sub_term(var(LV0), V), LV0 == LV, R = lvar(L, var(LV))
                     ; first_nguard(D, C, P), \+ boundary_guard(D, C), R = nguard(D, C, P) ) ), Here0),
        list_to_set(Here0, Here),
        findall(V, member(_-V, Defs), Vs), term_names(Vs, More),
        append(Xs, More, Next),
        data_deps(Next, Ls, Known, [X|Seen], Rest),
        append(Here, Rest, Deps)
    ).

term_names(T, Names) :- findall(N, (sub_term(var(N), T), atom(N)), Ns), sort(Ns, Names).

% ----- variabilise: names and statement ids become Prolog variables ----------
variabilise(Rels, VRels, NameVars) :-
    empty_assoc(M0), vt(Rels, VRels, M0, M),
    assoc_to_list(M, Pairs),
    name_values(Pairs, NameVars).          % no findall: it would copy the variables

name_values([], []).
name_values([n(_)-V|Ps], [V|Vs]) :- !, name_values(Ps, Vs).
name_values([_|Ps], Vs) :- name_values(Ps, Vs).

vt(var(N), var(V), M0, M) :- atom(N), !, key(n(N), V, M0, M).
vt(A, V, M0, M) :- atom(A), stmt(A, _, _, _), !, key(s(A), V, M0, M).
vt(call(N, As), call(V, Bs), M0, M) :-            % G7: helpers defined in this source
    atom(N), N \== '$self', func(_, FN, _), base_name(FN, N), !,
    key(f(N), V, M0, M1), vt(As, Bs, M1, M).
vt(T, T, M, M) :- atomic(T), !.
vt([H|T], [H1|T1], M0, M) :- !, vt(H, H1, M0, M1), vt(T, T1, M1, M).
vt(T, T1, M0, M) :- T =.. [F|As], vt(As, Bs, M0, M), T1 =.. [F|Bs].

key(K, V, M, M) :- get_assoc(K, M, V), !.
key(K, V, M0, M) :- put_assoc(K, M0, V, M).

% ----- quality gate (doc 04 G8): an algorithm iterates (loop or recursion) -------
% ... and it computes something: at least two relations that carry data or decisions,
% not only loop structure (a bare "return x inside two loops" is not an algorithm).
quality(Rels, usable) :-
    memberchk(under(_, _), Rels), length(Rels, N), N >= 3,
    (   N >= 4, include(content, Rels, C), length(C, NC), NC >= 2
    ;   member(value(D, var(X), E), Rels), member(under(D, _), Rels),   % accumulator
        sub_term(var(Y), E), Y == X,                                    % recurrence x = f(x, ...)
        \+ counter(X, E)                                                % ... not just x + 1
    ;   member(cret(_, R), Rels), R \= call('$self', _),                % recursive computation
        sub_term(call('$self', _), R)                                   % n * f(...), f(..) + f(..)
    ), !.
quality(_, trivial).

content(exchange(_, _, _, _)).
content(value(_, var(X), E)) :- !, \+ counter(X, E).    % a counter update is not a computation
content(value(_, _, _)).
content(capp(_, _, _)).
content(nguard(_, _, _)).
content(lcond(_, _)).
content(cret(_, V)) :- V \= var(_), V \= call('$self', _).

% x = x + c / x - c: a counter, not a computation
counter(X, op(O, [var(Y), int(_)])) :- memberchk(O, [add, sub]), Y == X.
counter(X, op(add, [int(_), var(Y)])) :- Y == X.

/* AP13 logic tracing: backward slice from a function's outputs (Weiser 1984)
   over control dependences (guards, enclosing loops) and data dependences
   (loop-carried definitions), on the language-neutral canonical relations.
   The slice is a list of ground relations; docstrings, input validation and
   initialisation outside the loops are never reached (doc 01 section 8).
*/

% Effects (outputs) of F and of the functions it calls.
effect(F, exchange(S, Q, I, J)) :-
    reaches(F, G), stmt(S, G, _, _), once(exchange(S, Q, I, J)).
effect(F, value(S, elem(Q, I), V)) :-
    reaches(F, G), stmt(S, G, _, _), value(S, elem(Q, I), V), \+ exchange(S, _, _, _).
effect(F, ret(S, V)) :-
    reaches(F, G), stmt(S, G, _, _), ret(S, V), live(S), under(S, _),
    V \= int(_), V \= other(_), V \= call(_, _).

effect_stmt(exchange(S, _, _, _), S).
effect_stmt(value(S, _, _), S).
effect_stmt(ret(S, _), S).

slice(F, Rels) :-
    findall(E, effect(F, E), Es0), sort(Es0, Es),
    Es \== [],
    foldl(effect_relations(F), Es, [], R0),
    reverse(R0, R1), list_to_set(R1, Rels).

effect_relations(F, E, Acc0, Acc) :-
    effect_stmt(E, S),
    findall(L, under(S, L), Ls0), sort(Ls0, Ls),
    stmt_relations(S, Ls, Ctl),
    findall(under(L1, L2), (member(L1, Ls), member(L2, Ls), L1 \== L2, under(L1, L2)), Nest),
    findall(lcond(L, C), (member(L, Ls), loop(L, _, K), K \== count, once(lcond(L, C))), Conds),
    term_names([E|Ctl], Used),
    findall(lvar(L, var(V)), (member(L, Ls), loop_var(L, V), memberchk(V, Used)), LVars),
    loop_names(Ls, LoopNames),
    inputs(F, Inputs),
    append([LoopNames, Inputs], Known),
    data_deps(Used, Ls, Known, [], Deps),
    append([[E], Ctl, Nest, Conds, LVars, Deps], New),
    reverse(New, RNew), append(RNew, Acc0, Acc).

% guards and enclosing loops of one statement (control dependence)
stmt_relations(S, Ls, Rels) :-
    findall(nguard(S, C, P), first_nguard(S, C, P), Gs),
    findall(under(S, L), member(L, Ls), Us),
    append(Gs, Us, Rels).

first_nguard(S, C, P) :-
    guard(S, C0, P0), C0 \= bool(_), norm_pol(C0, P0, C, P).

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
                     ; first_nguard(D, C, P), R = nguard(D, C, P) ) ), Here),
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
vt(T, T, M, M) :- atomic(T), !.
vt([H|T], [H1|T1], M0, M) :- !, vt(H, H1, M0, M1), vt(T, T1, M1, M).
vt(T, T1, M0, M) :- T =.. [F|As], vt(As, Bs, M0, M), T1 =.. [F|Bs].

key(K, V, M, M) :- get_assoc(K, M, V), !.
key(K, V, M0, M) :- put_assoc(K, M0, V, M).

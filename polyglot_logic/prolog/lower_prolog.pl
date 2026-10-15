/* AP13 transform: Prolog source -> the same language-neutral base facts.
   Uses SWI-Prolog's own reader (read_term/3); the source is never consulted
   or executed. Recursion is a loop, guards before ! or -> are guard/3, list
   patterns [X,Y|T] address positions $cursor, $cursor+1 (doc 01 section 7).
   Run: swipl -q -s lower_prolog.pl -g lower_main -t halt -- Source.pl
*/
:- use_module(library(lists)).
:- use_module(library(apply)).

lower_main :-
    current_prolog_flag(argv, [File|_]),
    read_clauses(File, Clauses),
    format('lang(~q).~n', [prolog]),
    flag(ap13_id, _, 0),
    group_by_predicate(Clauses, Groups),
    forall(member(Key-Cs, Groups),
           (   lower_predicate(Key, Cs) -> true
           ;   format(user_error, 'AP13: lowering failed for ~q~n', [Key]), halt(2)
           )).

read_clauses(File, Clauses) :-
    setup_call_cleanup(open(File, read, S, [encoding(utf8)]),
                       read_all(S, Clauses),
                       close(S)).

read_all(S, Clauses) :-
    read_term(S, T, [variable_names(Vs), term_position(P)]),
    (   T == end_of_file
    ->  Clauses = []
    ;   stream_position_data(line_count, P, Line),
        maplist(bind_name, Vs),
        term_variables(T, Anon), maplist(=(v('_')), Anon),
        (   T = (:- _)
        ->  Clauses = Rest
        ;   Clauses = [clause(T, Line)|Rest]
        ),
        read_all(S, Rest)
    ).

bind_name(Name=v(Name)).

clause_parts((H :- B), H, B) :- !.
clause_parts(H, H, true).

group_by_predicate(Clauses, Groups) :-
    findall(N/A, (member(clause(T, _), Clauses), clause_parts(T, H, _), functor(H, N, A)), Keys0),
    list_to_set(Keys0, Keys),
    findall(K-Cs, (member(K, Keys),
                   findall(C, (member(C, Clauses), C = clause(T, _), clause_parts(T, H, _),
                               functor(H, N, A), K == N/A), Cs)), Groups).

new_id(Prefix, Id) :-
    flag(ap13_id, N, N+1), N1 is N+1, atom_concat(Prefix, N1, Id).

emit(Fact) :- format('~q.~n', [Fact]).

% ----- one predicate = one function -------------------------------------------
lower_predicate(Name/Arity, Clauses) :-
    Clauses = [clause(_, Line0)|_],
    nb_setval(ap13_current, Name/Arity),
    new_id(f, F),
    format(atom(Qualified), '~w/~w', [Name, Arity]),
    emit(func(F, Qualified, Line0)),
    params(Arity, Clauses, Params),
    forall(nth0(K, Params, P), emit(param(F, K, P))),
    (   member(clause(T, _), Clauses), clause_parts(T, _, B), body_calls(B, Name, Arity)
    ->  new_id(s, L), emit(stmt(L, F, loop, Line0)), emit(loop(L, F, recursion)), Loop = L
    ;   Loop = none
    ),
    (   catch(( outputs(Name, Arity, Clauses, Params, Outs),
                    with_output_to(string(Text),
                        lower_clauses(Clauses, Name/Arity, Params, Outs, ctx(F, Loop, []), [])) ),
                  _, fail)
    ->  write(Text)
    ;   emit(unsupported(F, 'clause form not modelled', Line0))   % explicit, never a guess
    ).

params(0, _, []) :- !.
params(Arity, Clauses, Params) :-
    numlist(1, Arity, Ns),
    maplist(param_name(Clauses), Ns, Params).

param_name(Clauses, N, P) :-
    (   member(clause(T, _), Clauses), clause_parts(T, H, _), arg(N, H, v(P0)), P0 \== '_'
    ->  P = P0
    ;   K is N - 1, format(atom(P), '$arg~w', [K])
    ).

body_calls(B, Name, Arity) :-
    body_goal(B, G), callable(G), functor(G, Name, Arity).

body_goal(V, _) :- var(V), !, fail.
body_goal((A, B), G) :- !, ( body_goal(A, G) ; body_goal(B, G) ).
body_goal((A ; B), G) :- !, ( body_goal(A, G) ; body_goal(B, G) ).
body_goal((A -> B), G) :- !, ( body_goal(A, G) ; body_goal(B, G) ).
body_goal(G, G).

% Output positions: the recursive call passes on a variable that the head also
% exposes at that position (pass-through) or as the tail of a head list [Y|R].
outputs(Name, Arity, Clauses, _Params, Outs) :-
    findall(K, ( member(clause(T, _), Clauses), clause_parts(T, H, B),
                 body_goal(B, G), callable(G), functor(G, Name, Arity),
                 arg(K, G, v(V)), V \== '_', arg(K, H, HA),
                 ( HA == v(V) -> true
                 ; HA = [_|Tail], Tail == v(V), elements_seen_before(HA, K, H)
                 ),
                 \+ used_outside(B, V, Name, Arity) ), Ks0),
    sort(Ks0, Outs).

% An output list [Y|R] re-emits elements that earlier head arguments introduced;
% an input pattern [X|T] introduces fresh variables.
elements_seen_before([E|_], K, H) :-
    E = v(Name), K0 is K - 1, between(1, K0, J), arg(J, H, Earlier),
    sub_term(S, Earlier), S == v(Name), !.

used_outside(B, V, Name, Arity) :-
    body_goal(B, G), callable(G), \+ functor(G, Name, Arity),
    \+ ( G = (X = _), X == v(V) ),
    sub_term(S, G), S == v(V), !.

% ----- clauses ---------------------------------------------------------------
lower_clauses([], _, _, _, _, _).
lower_clauses([clause(T, Line)|Cs], Key, Params, Outs, Ctx0, Pending) :-
    clause_parts(T, H, B),
    H =.. [_|Args],
    add_guards(Pending, Ctx0, Ctx1),
    head_env(Args, 1, Params, Outs, [], Env, Ctx1, Ctx2, Emits, In),
    ( In = list(_) , Ctx2 = ctx(_, Loop, _), Loop \== none -> emit(loop_var(Loop, '$cursor')) ; true ),
    body_list(B, Goals),
    emitted_count(Emits, Count), nb_setval(ap13_emitted, Count), nb_setval(ap13_writes, []),
    lower_goals(Goals, Key, Params, Outs, Env, Ctx2, In, Emits, Line, GuardsBeforeCut, Cut),
    flush_writes(Line),
    base_case_cond(B, Key, Ctx2, GuardsBeforeCut),
    (   Cut == true, GuardsBeforeCut \== []
    ->  negate_all(GuardsBeforeCut, Neg), append(Pending, Neg, Pending1)
    ;   Pending1 = Pending
    ),
    lower_clauses(Cs, Key, Params, Outs, Ctx0, Pending1).

% Writes of one clause happen simultaneously: one par_assign per guard context.
emitted_count(Emits, Count) :-
    findall(N, (member(out(L), Emits), is_list_prefix(L, N)), Ns), sum_list(Ns, Count).
is_list_prefix([_|T], N) :- !, ( var(T) -> N = 1 ; is_list_prefix(T, N0), N is N0 + 1 ).
is_list_prefix(_, 0).

add_write(Ctx, T, V) :-
    nb_getval(ap13_writes, W0), append(W0, [Ctx-(T-V)], W1), nb_setval(ap13_writes, W1).

flush_writes(Line) :-
    nb_getval(ap13_writes, W), nb_setval(ap13_writes, []),
    findall(C, member(C-_, W), Cs0), list_to_set(Cs0, Cs),
    forall(member(C, Cs),
           ( findall(T-V, (member(C1-(T-V), W), C1 == C, T \== V), Pairs),
             (   Pairs == [] -> true
             ;   pairs_keys_values(Pairs, Ts, Vs), stmt(C, assign, Line, S), emit(par_assign(S, Ts, Vs))
             ) )).

% A clause that does not recurse ends the loop: its two-variable guards give loop_cond.
base_case_cond(B, Name/Arity, ctx(_, Loop, _), Guards) :-
    (   Loop \== none, \+ body_calls(B, Name, Arity)
    ->  forall(( member(op(O, [var(X), var(Y)])-true, Guards) ),
               emit(loop_cond(Loop, op(not, [op(O, [var(X), var(Y)])]))))
    ;   true
    ).

add_guards([], C, C).
add_guards([G-P|Gs], ctx(F, L, G0), C) :- append(G0, [G-P], G1), add_guards(Gs, ctx(F, L, G1), C).

negate_all([], []).
negate_all([G-true|Gs], [G-false|Ns]) :- negate_all(Gs, Ns).
negate_all([G-false|Gs], [G-true|Ns]) :- negate_all(Gs, Ns).

body_list(true, []) :- !.
body_list((A, B), Gs) :- !, body_list(A, G1), body_list(B, G2), append(G1, G2, Gs).
body_list(G, [G]).

% Head arguments: inputs bind names to parameters / positions; outputs are kept.
head_env([], _, _, _, Env, Env, C, C, [], none).
head_env([A|As], N, Params, Outs, Env0, Env, C0, C, Emits, In) :-
    nth1(N, Params, P), N1 is N + 1,
    (   memberchk(N, Outs)
    ->  Emits = [out(A)|Rest], Env1 = Env0, C1 = C0, In1 = none
    ;   head_arg(A, P, Env0, Env1, C0, C1, In1), Emits = Rest
    ),
    head_env(As, N1, Params, Outs, Env1, Env, C1, C, Rest, In2),
    ( In1 = list(_) -> In = In1 ; In = In2 ).

head_arg(v('_'), _, E, E, C, C, none) :- !.
head_arg(v(X), P, E, [X-var(P)|E], C, C, none) :- !.
head_arg([], P, E, E, C0, C, none) :- !,
    add_guards([op(eq, [call(len, [var(P)]), int(0)])-true], C0, C).
head_arg(I, P, E, E, C0, C, none) :- integer(I), !,
    add_guards([op(eq, [var(P), int(I)])-true], C0, C).
head_arg([H|T], P, E0, E, C, C, list(P)) :- !,
    list_elems([H|T], 0, P, E0, E).
head_arg(_, _, E, E, C, C, none).

list_elems(v(T), K, P, E, [T-tail(var(P), K)|E]) :- !.
list_elems([], _, _, E, E) :- !.
list_elems([v(X)|R], K, P, E0, E) :- !,
    at(K, Pos), K1 is K + 1,
    list_elems(R, K1, P, [X-elem(var(P), Pos)|E0], E).
list_elems([_|R], K, P, E0, E) :- K1 is K + 1, list_elems(R, K1, P, E0, E).

at(0, var('$cursor')) :- !.
at(K, op(add, [var('$cursor'), int(K)])).

% ----- body goals -----------------------------------------------------------
lower_goals(Goals, Key, Params, Outs, Env, Ctx, In, Emits, Line, GuardsBeforeCut, Cut) :-
    goals(Goals, Key, Params, Outs, Env, Ctx, In, Line, CtxEnd, Cut),
    CtxEnd = ctx(_, _, AllGuards), Ctx = ctx(_, _, G0), append(G0, GuardsBeforeCut0, AllGuards),
    GuardsBeforeCut = GuardsBeforeCut0,
    emit_head_outputs(Emits, Env, CtxEnd, In, Line).

emit_head_outputs(Emits, Env, Ctx, In, Line) :-
    findall(E, member(out(E), Emits), Outs),
    forall(member(O, Outs), head_output(O, Env, Ctx, In, Line)).

head_output(v(_), _, _, _, _) :- !.                    % pass-through variable
head_output(I, _, Ctx, _, Line) :- integer(I), !, stmt(Ctx, ret, Line, S), emit(ret(S, int(I))).
head_output(L, Env, Ctx, list(P), _) :- L = [_|_], !,   % emitted elements at cursor + k
    out_writes(L, 0, P, Env, Ctx).
head_output(_, _, _, _, _).

out_writes([H|T], K, P, Env, Ctx) :- !,
    expr(Env, H, V), at(K, Pos), add_write(Ctx, elem(var(P), Pos), V),
    K1 is K + 1, ( var(T) -> true ; out_writes(T, K1, P, Env, Ctx) ).
out_writes(_, _, _, _, _).

goals([], _, _, _, _, Ctx, _, _, Ctx, false).
goals([G|Gs], Key, Params, Outs, Env, Ctx, In, Line, CtxEnd, Cut) :-
    goal(G, Key, Params, Outs, Env, Env1, Ctx, Ctx1, In, Line, C1),
    goals(Gs, Key, Params, Outs, Env1, Ctx1, In, Line, CtxEnd, C2),
    ( (C1 == true ; C2 == true) -> Cut = true ; Cut = false ).

goal(!, _, _, _, E, E, C, C, _, _, true) :- !.
goal(G, _, _, _, E, E, C0, C, _, _, false) :-
    compare_goal(G, Op, A, B), !,
    expr(E, A, X), expr(E, B, Y), add_guards([op(Op, [X, Y])-true], C0, C).
goal((X is Ex), _, _, Outs, E, E, C, C, _, Line, false) :- !,
    expr(E, Ex, V),
    (   output_var(X, Outs, _) -> stmt(C, ret, Line, S), emit(ret(S, V))
    ;   X = v(N), stmt(C, assign, Line, S), emit(assign(S, var(N), V))
    ).
goal(nth0(I, L, v(V)), _, _, _, E, [V-elem(LV, IV)|E], C, C, _, _, false) :- !,
    expr(E, L, LV), expr(E, I, IV).
goal(nth1(I, L, v(V)), _, _, _, E, [V-elem(LV, IV)|E], C, C, _, _, false) :- !,
    expr(E, L, LV), expr(E, I, IV).
goal(length(L, v(N)), _, _, _, E, E, C, C, _, Line, false) :- !,
    expr(E, L, LV), stmt(C, assign, Line, S), emit(assign(S, var(N), call(len, [LV]))).
goal((v(X) = Rhs), Key, Params, Outs, E, E1, C, C, _, Line, false) :- !,
    expr(E, Rhs, V),
    (   output_name(X, Key, Params, Outs) -> stmt(C, ret, Line, S), emit(ret(S, V)), E1 = E
    ;   E1 = [X-V|E]
    ).
goal((If -> Then ; Else), Key, Params, Outs, E, E, C, C, In, Line, false) :- !,
    body_list(If, IfGs), goals(IfGs, Key, Params, Outs, E, C, In, Line, CIf, _),
    C = ctx(_, _, G0), CIf = ctx(F, L, GIf), append(G0, New, GIf),
    body_list(Then, ThenGs), goals(ThenGs, Key, Params, Outs, E, CIf, In, Line, _, _),
    negate_all(New, Neg), add_guards(Neg, ctx(F, L, G0), CElse),
    body_list(Else, ElseGs), goals(ElseGs, Key, Params, Outs, E, CElse, In, Line, _, _).
goal(G, Name/Arity, Params, Outs, E, E, C, C, In, Line, false) :-
    callable(G), functor(G, Name, Arity), !,
    G =.. [_|Args],
    maplist(expr(E), Args, Vs), stmt(C, call, Line, S), emit(call_at(S, '$self', Vs)),
    emit(ret(S, call('$self', Vs))),                 % a tail self-call is the result
    forall(nth1(K, Args, A), recursive_arg(K, A, Params, Outs, E, C, In, Line-S)).
goal(G, _, _, _, E, E, C, C, _, Line, false) :-
    callable(G), functor(G, N, _), memberchk(N, [(;), (','), (->), (\+), (*->)]), !,
    C = ctx(F, _, _), emit(unsupported(F, 'nested control construct', Line)).
goal(G, _, _, _, E, E, C, C, _, Line, false) :-
    callable(G), G =.. [N|Args], maplist(expr(E), Args, Vs),
    stmt(C, call, Line, S), emit(call_at(S, N, Vs)).

recursive_arg(K, _, _, Outs, _, _, _, _) :- memberchk(K, Outs), !.
recursive_arg(K, [H|T], Params, _, E, C, list(P), Line0) :- !,  % continue with [X|Rest]
    ( Line0 = Line-_ -> true ; Line = Line0 ),
    nth1(K, Params, P), P = P, nb_getval(ap13_emitted, Start),
    cons_writes([H|T], Start, P, E, Writes),
    forall(member(Tw-Vw, Writes), add_write(C, Tw, Vw)), Line = Line.
recursive_arg(K, A, Params, _, E, _, _, _-S) :-     % update on the call statement itself
    nth1(K, Params, P), expr(E, A, V),
    (   ( V == var(P) ; V = tail(_, _) ) -> true
    ;   emit(assign(S, var(P), V))
    ).

cons_writes(v(_), _, _, _, []) :- !.
cons_writes([], _, _, _, []) :- !.
cons_writes([X|R], K, P, E, [elem(var(P), Pos)-V|W]) :-
    at(K, Pos), expr(E, X, V), K1 is K + 1, cons_writes(R, K1, P, E, W).

identity(T-V) :- T == V.

output_var(v(X), Outs, X) :- Outs \== [], fail.   % 'is' into an output: handled by =
output_name(X, _/_, Params, Outs) :- member(K, Outs), nth1(K, Params, X), !.
output_name(X, Key, _, _) :- nb_current(ap13_head_outputs, L), memberchk(Key-X, L), !.

compare_goal(G, Op, A, B) :-
    G =.. [F, A, B], cmp_op(F, Op).
cmp_op(>, gt). cmp_op(<, lt). cmp_op(>=, ge). cmp_op(=<, le).
cmp_op(=:=, eq). cmp_op(=\=, ne). cmp_op(==, eq). cmp_op(\==, ne).

stmt(ctx(F, Loop, Guards), Kind, Line, S) :-
    new_id(s, S), emit(stmt(S, F, Kind, Line)),
    ( Loop \== none -> emit(in_loop(S, Loop)) ; true ),
    forall(member(G-P, Guards), emit(guard(S, G, P))).

% ----- expressions ---------------------------------------------------------
expr(E, v(X), T) :- !, ( memberchk(X-T0, E) -> T = T0 ; T = var(X) ).
expr(_, I, int(I)) :- integer(I), !.
expr(E, -(A), T) :- !, expr(E, A, X), ( X = int(N) -> M is -N, T = int(M) ; T = op(neg, [X]) ).
expr(E, G, op(Op, [X, Y])) :- compound(G), G =.. [F, A, B], arith_op(F, Op), !,
    expr(E, A, X0), expr(E, B, Y0), order_add(Op, X0, Y0, X, Y).
expr(E, [H|T], cons(X, Y)) :- !, expr(E, H, X), expr(E, T, Y).
expr(_, [], nil) :- !.
expr(E, G, call('$self', Xs)) :- compound(G), nb_current(ap13_current, N/A), functor(G, N, A), !,
    G =.. [_|As], maplist(expr(E), As, Xs).
expr(E, G, call(F, Xs)) :- compound(G), !, G =.. [F|As], maplist(expr(E), As, Xs).
expr(_, A, other(A)).

order_add(add, int(N), Y, Y, int(N)) :- Y \= int(_), !.
order_add(_, X, Y, X, Y).

arith_op(+, add). arith_op(-, sub). arith_op(*, mul). arith_op(//, div). arith_op(div, div).
arith_op(/, fdiv). arith_op(mod, mod). arith_op(rem, mod).
arith_op(F, Op) :- cmp_op(F, Op).

/* v0.2 shared logic-flow tokenizer (doc 03 section 9, doc 04): the neutral facts of a function
   (any language: AP13 lowerers, or the ECL export) written as a token stream in source order:
   tests (guards), assigned values, calls, loops, returns; a call of a function of the same file is
   a LINK whose statements are spliced in between enter(G) and leave(G) (at most 4 deep, acyclic).
   Used by fallback_main.pl (fallback rules) and flow_main.pl / learn_dcg.pl (learned rules).
*/
:- discontiguous stmt_term/3, tokens//4.
:- dynamic func/3, param/3, stmt/4, loop/3, in_loop/2, loop_var/2, loop_cond/2, loop_iter/2, guard/3, tail_loop/1,
           assign/3, par_assign/3, call_at/3, ret/2, family/3.

... --> [] | [_], ... .
% find(T): the next token that T matches (greedy; the tokens of a learned rule are independent, so the
% first occurrence is as good as any and no backtracking over gaps is needed)
find(T) --> [X], ( { \+ X \= T } -> { X = T } ; find(T) ).

% the root function: its statements in source order (assigned values, calls, returns); a linked
% function contributes its result values (link//4)
result_tokens(F, Ts) :- body_terms(F, Vs), Vs \== [], phrase(terms_tokens(F, [F], 4, Vs), Ts).
body_terms(F, Vs) :-
    findall(L-N-S, ( stmt(S, F, _, L), sub_atom(S, 1, _, 0, NA), atom_number(NA, N) ), Ks), msort(Ks, Sorted),
    findall(V, ( member(_-_-S, Sorted), stmt_term(F, S, V) ), Vs).
stmt_term(_, S, loop) :- stmt(S, F, loop, _), loop(S, F, K), K \== recursion, \+ tail_loop(S).   % a loop starts
stmt_term(_, S, guard(C)) :- guard(S, C, _).                 % the statement's conditions first
stmt_term(F, S, V) :- assign(S, T, V), T \= elem(other(field), _), \+ self_update(F, S, T).
% a recursive call's parameter updates (attached by the lowerers) repeat the call's arguments
self_update(F, S, var(P)) :- param(F, _, P),
    ( call_at(S, '$self', _) ; ( ret(S, V) ; assign(S, _, V) ), sub_term(C, V), compound(C), C = call('$self', _) ), !.
stmt_term(_, S, call(G, As)) :- call_at(S, G, As), G \== '$self'.
stmt_term(_, S, call('$self', As)) :- call_at(S, '$self', As),          % a self-call made as a statement
    \+ ( ( ret(S, V) ; assign(S, _, V) ), sub_term(C, V), compound(C), C = call('$self', _) ).
stmt_term(F, S, V) :- ret(S, V0), result_value(F, V0, V).
% ECL compiles a tail self-call as a jump to the function's start (tail_loop): it is the self-call it was,
% at the jump back, after the loop's last statement
stmt_term(F, S, call('$self', Args)) :- tail_loop(L), stmt(L, F, _, _), in_loop(S, L),
    \+ ( in_loop(S2, L), stmt(S2, F, _, L2), stmt(S, F, _, L1), ( L2 > L1 ; L2 =:= L1, S2 @> S ) ),
    findall(K-P, param(F, K, P), KPs), msort(KPs, Sorted), pairs_values(Sorted, Ps),
    maplist(tail_argument(F, L), Ps, Args).
% the argument of the tail call: the parameter's new value in the loop (ECL's parallel update)
tail_argument(F, L, P, V) :-
    (   in_loop(S, L), stmt(S, F, _, _), ( par_assign(S, Ts, Vs), nth1(K, Ts, T), T == var(P), nth1(K, Vs, V0)
                                         ; assign(S, T, V0), T == var(P) )
    ->  V = V0 ; V = var(P) ).
% (values a b) returns values[0] and sets values[1] in the same function: a returned values[k] is
% the term the function stored there
results(F, Vs) :- findall(V, ( ret(S, V0), stmt(S, F, _, _), result_value(F, V0, V) ), Vs).
result_value(F, elem(other(field), int(K)), V) :- assign(S, elem(other(field), int(K2)), V), K2 == K,
    stmt(S, F, _, _), !.
result_value(_, V, V).

terms_tokens(_, _, _, []) --> [].
terms_tokens(F, Path, D, [T|Ts]) --> tokens(F, Path, D, T), terms_tokens(F, Path, D, Ts).

% ----- the vocabulary: one token per construct, prefix order ---------------------------------
tokens(_, _, _, T) --> { var(T) }, !, [unknown].
tokens(F, P, D, call(Fold, [int(_), Fn, Q|Rest])) --> { memberchk(Fold, [cl_reduce, cl_apply]) }, !,
    [fold], tokens(F, P, D, Fn), tokens(F, P, D, Q), fold_init(F, P, D, Rest).
tokens(F, P, D, map(Q, Fn, Qs)) --> !, [map], tokens(F, P, D, Fn), terms_tokens(F, P, D, [Q|Qs]).
tokens(F, P, D, fn(G)) --> { linked(G) }, !, link(F, P, D, G).
tokens(_, _, _, fn(Op)) --> !, [op(Op)].
tokens(F, P, D, call(ecl_make_cclosure_va, [var(C)|_])) --> { closure_name(C, G), linked(G) }, !, link(F, P, D, G).
tokens(F, P, D, call(G, As)) --> { linked(G) }, !, link(F, P, D, G), terms_tokens(F, P, D, As).
tokens(F, P, D, call(cl_member_if_not, [int(_), Pr, Q])) --> !, [split_point], tokens(F, P, D, Pr), tokens(F, P, D, Q).
tokens(F, P, D, call(cl_ldiff, [Q, T])) --> !, [prefix_until], tokens(F, P, D, Q), tokens(F, P, D, T).
tokens(F, P, D, concat(Parts)) --> !, { length(Parts, N) }, [append(N)], terms_tokens(F, P, D, Parts).
tokens(F, P, D, call(cl_position, [int(_), X, Q|_])) --> !, [position], tokens(F, P, D, X), tokens(F, P, D, Q).
tokens(F, P, D, call(cl_subseq, [int(_)|As])) --> !, [subseq], terms_tokens(F, P, D, As).
tokens(F, P, D, call(cl_replace, [int(_), Q, R|_])) --> !, [replace], tokens(F, P, D, Q), tokens(F, P, D, R).
tokens(F, P, D, call(reverse, [Q])) --> !, [reverse], tokens(F, P, D, Q).
tokens(F, P, D, list([X])) --> !, [single], tokens(F, P, D, X).
tokens(F, P, D, guard(C)) --> !, [test], tokens(F, P, D, C).
tokens(F, P, D, cons(A, B)) --> !, [cons], tokens(F, P, D, A), tokens(F, P, D, B).
tokens(F, P, D, tail(Q, _)) --> !, [rest], tokens(F, P, D, Q).
tokens(_, _, _, elem(other(field), int(K))) --> !, [value(K)].        % (values a b): the K-th value
tokens(F, P, D, op(O, As)) --> { memberchk(O, [lt, le, gt, ge]) }, !, [cmp(O)], terms_tokens(F, P, D, As).
tokens(F, P, D, op(O, As)) --> !, [op(O)], terms_tokens(F, P, D, As).
tokens(F, P, D, elem(Q, I)) --> !, [elem], tokens(F, P, D, Q), tokens(F, P, D, I).
tokens(F, _, _, var(X)) --> { param(F, _, X) }, !, [param].
tokens(_, _, _, var(_)) --> !, [local].
tokens(_, _, _, bool(false)) --> !, [empty].
tokens(_, _, _, list([])) --> !, [empty].
tokens(_, _, _, int(N)) --> !, [int(N)].
tokens(F, P, D, call(G, As)) --> { output_call(G) }, !, [output], terms_tokens(F, P, D, As).
tokens(F, P, D, call(G, As)) --> !, [call(G)], terms_tokens(F, P, D, As).
tokens(_, _, _, loop) --> !, [loop].
tokens(_, _, _, _) --> [other].
% printing is an effect, not the logic: one token in every language
output_call(G) :- memberchk(G, [print, println, printf, puts, putchar, putStrLn, putStr, print_newline, mapM_, cl_format,
                               cl_print, ecl_print, cl_princ, cl_prin1, cl_terpri, cl_write_line, cl_write_string,
                               format, display, write, writeln]), !.

fold_init(F, P, D, [call(ecl_keyword, [var(initial_value)]), V|_]) --> !, [init], tokens(F, P, D, V).
fold_init(_, _, _, _) --> [].

% a link to a function of this file: its result tokens in between, bounded and acyclic
link(_, P, D, G) --> { func_named(G, H), ( D =< 0 ; memberchk(H, P) ) }, !, [link(G)].
link(_, P, D, G) --> { func_named(G, H), D1 is D - 1, body_terms(H, Vs) },
    [link(G), enter(G)], terms_tokens(H, [H|P], D1, Vs), [leave(G)].
linked(G) :- atom(G), func_named(G, _), !.
% a function of the file by its own name or its base name (Python's nested hanoi.go is go)
func_named(G, H) :- func(H, G, _), !.
func_named(G, H) :- func(H, N, _), atomic_list_concat(Parts, '.', N), last(Parts, G), !.
closure_name(C, G) :- atom(C), atom_codes(C, [0'L, 0'C|Cs]), drop_digits(Cs, Ns), atom_codes(G, Ns).
drop_digits([D|Cs], Ns) :- code_type(D, digit), !, drop_digits(Cs, Ns).
drop_digits(Ns, Ns).

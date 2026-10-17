/* v0.2 fallback (doc 03 section 9), SEPARATE from the normal process. It reads only the normal
   process's exported output (ecl_main.pl ecl_export: the facts after ecl_norm and the FAMILY
   answers) and answers, for a function the normal process gave no v0.2 branch, by deterministic
   pattern rules (prolog/fallback_rules.pl, DCGs) over a token stream of the function's result:
     - every result term is written in prefix order as tokens (tokens//3 below, a DCG too);
     - a call of (or a function object naming) a function of the same file is a LINK: its result
       tokens are spliced in between enter(G) and leave(G), at most 4 deep and never re-entering a
       function already on the path, so the walk always ends;
     - fallback_pattern(Branch, Rule)//0 rules parse the stream; the first that parses answers.
   fallback_main -- Export : FALLBACK|F|Name|Branch|Rule lines
*/
:- dynamic func/3, param/3, stmt/4, loop/3, in_loop/2, loop_var/2, loop_cond/2, loop_iter/2, guard/3,
           assign/3, par_assign/3, call_at/3, ret/2, family/3.
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'fallback_rules.pl', R), load_files(R, []).

fallback_main :-
    current_prolog_flag(argv, [Export|_]), load_files(Export, [if(true)]),
    forall(( func(F, Name, _), \+ answered(F), result_tokens(F, Ts), once(phrase(fallback_pattern(B, Rule), Ts)) ),
           format('FALLBACK|~w|~w|~w|~w~n', [F, Name, B, Rule])).
answered(F) :- family(F, _, B), B \== none, !.

% the function's results: its returned values, in statement order
% the root function: its statements in source order (assigned values, calls, returns); a linked
% function contributes its result values (link//4)
result_tokens(F, Ts) :- body_terms(F, Vs), Vs \== [], phrase(terms_tokens(F, [F], 4, Vs), Ts).
body_terms(F, Vs) :-
    findall(L-N-S, ( stmt(S, F, _, L), sub_atom(S, 1, _, 0, NA), atom_number(NA, N) ), Ks), msort(Ks, Sorted),
    findall(V, ( member(_-_-S, Sorted), stmt_term(F, S, V) ), Vs).
stmt_term(_, S, V) :- assign(S, T, V), T \= elem(other(field), _).
stmt_term(_, S, call(G, As)) :- call_at(S, G, As), G \== '$self'.
stmt_term(F, S, V) :- ret(S, V0), result_value(F, V0, V).
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
tokens(_, _, _, elem(other(field), int(K))) --> !, [value(K)].        % (values a b): the K-th value
tokens(F, P, D, op(O, As)) --> { memberchk(O, [lt, le, gt, ge]) }, !, [cmp(O)], terms_tokens(F, P, D, As).
tokens(F, P, D, op(O, As)) --> !, [op(O)], terms_tokens(F, P, D, As).
tokens(F, P, D, elem(Q, I)) --> !, [elem], tokens(F, P, D, Q), tokens(F, P, D, I).
tokens(F, _, _, var(X)) --> { param(F, _, X) }, !, [param].
tokens(_, _, _, var(_)) --> !, [local].
tokens(_, _, _, bool(false)) --> !, [empty].
tokens(_, _, _, list([])) --> !, [empty].
tokens(_, _, _, int(N)) --> !, [int(N)].
tokens(F, P, D, call(G, As)) --> !, [call(G)], terms_tokens(F, P, D, As).
tokens(_, _, _, _) --> [other].

fold_init(F, P, D, [call(ecl_keyword, [var(initial_value)]), V|_]) --> !, [init], tokens(F, P, D, V).
fold_init(_, _, _, _) --> [].

% a link to a function of this file: its result tokens in between, bounded and acyclic
link(_, P, D, G) --> { func(H, G, _), ( D =< 0 ; memberchk(H, P) ) }, !, [link(G)].
link(_, P, D, G) --> { func(H, G, _), D1 is D - 1, results(H, Vs) },
    [link(G), enter(G)], terms_tokens(H, [H|P], D1, Vs), [leave(G)].
linked(G) :- atom(G), func(_, G, _), !.
closure_name(C, G) :- atom(C), atom_codes(C, [0'L, 0'C|Cs]), drop_digits(Cs, Ns), atom_codes(G, Ns).
drop_digits([D|Cs], Ns) :- code_type(D, digit), !, drop_digits(Cs, Ns).
drop_digits(Ns, Ns).

/* AP13 leaf matching: a learned reference is a conjunction of canonical
   relations with shared Prolog variables (GRASPR/IDL style). It matches only
   when ALL relations hold with ONE consistent binding and distinct names.
   Otherwise the report says which relations are missing - never a weaker match.
*/
:- dynamic reference/4.

holds(Rels, Names) :-
    maplist(call, Rels),
    all_distinct_atoms(Names).

all_distinct_atoms(Names) :- msort(Names, S), sort(Names, S2), length(S, N), length(S2, N).

leaf_result(Label, Branch, match(Bindings, Funcs, Cover)) :-
    reference(Label, Branch, Rels, Names),
    copy_term(Rels-Names, R-N),
    once(holds(R, N)),
    bindings(N, Bindings),
    involved_functions(R, Funcs),
    cover(R, Cover).

leaf_result(Label, Branch, partial(Missing, Present, Total)) :-
    reference(Label, Branch, Rels, Names),
    \+ ( copy_term(Rels-Names, R-N), holds(R, N) ),
    length(Rels, Total),
    findall(Rel, (member(Rel0, Rels), copy_term(Rel0, Rel), \+ call(Rel)), Missing0),
    length(Missing0, NMissing), Present is Total - NMissing,
    Present * 2 >= Total,
    maplist(describe, Missing0, Missing).

% Recognition must COVER the program (Wills, GRASPR): a match explains a function
% only if every effect of the involved functions (exchange, element write, append,
% computed return) is one of the matched statements. Otherwise the function merely
% CONTAINS the algorithm (a cocktail sort contains a bubble pass; an lcm contains a gcd).
cover(R, Cover) :-
    findall(S, (sub_term(S, R), atom(S), stmt(S, _, _, _)), Bound0), sort(Bound0, Bound),
    findall(F, (member(S, Bound), stmt(S, F, _, _)), Fs0), sort(Fs0, Fs),
    (   member(F, Fs), effect(F, E), \+ plumbing(E), effect_stmt(E, S), stmt(S, F, _, _),
        \+ memberchk(S, Bound)
    ->  Cover = part
    ;   Cover = full
    ).

% returning a bare recursive call, or delegating to a function of the same program,
% computes nothing itself (doc 05 Q13)
plumbing(cret(_, call('$self', _))).
plumbing(cret(_, call(G, _))) :- func(_, Name, _), base_name(Name, G).
bindings(Names, Names).

involved_functions(Rels, Funcs) :-
    findall(Name, (sub_term(S, Rels), atom(S), stmt(S, F, _, _), func(F, Name, _)), Fs),
    sort(Fs, Funcs).

describe(Rel, Desc) :- Rel =.. [F|_], Desc = F.

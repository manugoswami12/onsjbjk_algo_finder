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

leaf_result(Label, Branch, match(Bindings, Funcs)) :-
    reference(Label, Branch, Rels, Names),
    copy_term(Rels-Names, R-N),
    once(holds(R, N)),
    bindings(N, Bindings),
    involved_functions(R, Funcs).
leaf_result(Label, Branch, partial(Missing, Present, Total)) :-
    reference(Label, Branch, Rels, Names),
    \+ ( copy_term(Rels-Names, R-N), holds(R, N) ),
    length(Rels, Total),
    findall(Rel, (member(Rel0, Rels), copy_term(Rel0, Rel), \+ call(Rel)), Missing0),
    length(Missing0, NMissing), Present is Total - NMissing,
    Present * 2 >= Total,
    maplist(describe, Missing0, Missing).

bindings(Names, Names).

involved_functions(Rels, Funcs) :-
    findall(Name, (sub_term(S, Rels), atom(S), stmt(S, F, _, _), func(F, Name, _)), Fs),
    sort(Fs, Funcs).

describe(Rel, Desc) :- Rel =.. [F|_], Desc = F.

/* The canonical form of an exact-logic pattern (doc 04 section 19.13), on the term (logic_canon.py calls it once per
   learned file). A pattern reference(Label, Branch, Relations, Vars) keeps the algorithm's logic, written the same in
   every language; dropped or abstracted is what is not:
     an input check  nguard(S, G, P) with G a parameter compared with a constant (if n <= 0: return False), on every
                     statement of the pattern: the function's context (as families_v02.pl continuation_guard treats it)
     a range bound   call(range, [Lo, Hi]): how far the search runs, not what it computes (n // 2 + 1, n - 1): Hi a
                     variable of the pattern, the same Hi term the same variable
   Vars keeps only the variables still in Relations (an abstracted bound's variables are gone).
     canon_main -- In Out : every reference/4 term of In, canonical, written to Out (portray_clause), in order
*/
canon_main :-
    current_prolog_flag(argv, [In, Out|_]),
    read_file_to_terms(In, Terms, []),
    setup_call_cleanup(open(Out, write, S), forall(member(T, Terms), ( canonical(T, C), portray_clause(S, C) )), close(S)).

canonical(reference(L, B, Rels0, Vs0), reference(L, B, Rels, Vs)) :- !,
    statements(Rels0, Ss),
    exclude(context_check(Rels0, Ss), Rels0, Rels1),
    abstract_ranges(Rels1, Rels, []-_),
    term_variables(Rels, In),
    include(occurs_in(In), Vs0, Vs).
canonical(T, T).
occurs_in(Vars, V) :- member(W, Vars), W == V, !.

% the statements the pattern names: the first argument of its statement relations (collected without copying:
% findall would rename the variables, and a statement is compared with ==)
statements(Rels, Ss) :- statement_args(Rels, Ss0), dedup(Ss0, Ss).
statement_args([], []).
statement_args([R|Rs], Ss) :-
    (   compound(R), R =.. [F, S|_], memberchk(F, [cret, value, capp, under, nguard])
    ->  Ss = [S|Ss1] ; Ss = Ss1 ),
    statement_args(Rs, Ss1).
dedup([], []).
dedup([X|Xs], [X|Ys]) :- exclude(==(X), Xs, Xs1), dedup(Xs1, Ys).

% an input check on every statement
context_check(Rels, Ss, nguard(_, G, P)) :-
    input_check(G),
    forall(member(S, Ss), ( member(R, Rels), R = nguard(S2, G2, P2), S2 == S, G2 == G, P2 == P )).
input_check(op(Op, [X, Y])) :- memberchk(Op, [ge, gt, le, lt, eq]),
    ( X = int(_), nonvar(Y), Y = var(_) ; Y = int(_), nonvar(X), X = var(_) ), !.

% call(range, [Lo, Hi]) -> call(range, [Lo, V]), one V per Hi term (Map: Hi-V pairs)
abstract_ranges(T0, T, M0-M) :- var(T0), !, T = T0, M = M0.
abstract_ranges(T0, T, M0-M) :- nonvar(T0), T0 = call(Range, [Lo0, Hi]), Range == range, !,
    abstract_ranges(Lo0, Lo, M0-M1),
    ( member(H-V, M1), H == Hi -> M = M1 ; M = [Hi-V|M1] ),
    T = call(range, [Lo, V]).
abstract_ranges(T0, T, M0-M) :- compound(T0), !, T0 =.. [F|As0], foldl_args(As0, As, M0-M), T =.. [F|As].
abstract_ranges(T, T, M-M).
foldl_args([], [], M-M).
foldl_args([A0|As0], [A|As], M0-M) :- abstract_ranges(A0, A, M0-M1), foldl_args(As0, As, M1-M).

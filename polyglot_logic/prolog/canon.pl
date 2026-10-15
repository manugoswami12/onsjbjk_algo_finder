/* AP13 canonicalisation (Metzger & Wen: reduce program variation before matching).
   Reads only the language-neutral base facts; adds canonical relations:
     exchange/4  swap idioms of all languages
     nguard/3    guards with comparison direction and negation normalised
     lcond/2     loop continuation condition, normalised
     value/3     assignment value with single-definition copy propagation
     under/2     loop nesting, also through calls (recursion = loop)
     lvar/2      loop variable as var(Name)
     live/1      statement not under a constant-false guard
*/
:- table under/2, reaches/2.

% ----- statements ------------------------------------------------------------
live(S) :- stmt(S, _, _, _), \+ guard(S, bool(false), true), \+ guard(S, bool(true), false).
stmt_func(S, F) :- stmt(S, F, _, _).
stmt_line(S, L) :- stmt(S, _, _, L).

% ----- exchange: one canonical relation for every swap idiom (P8) -------------
exchange(S, Q, I, J) :- raw_exchange(S, Q, I1, J1), live(S),
    shift_term(S, I1, I0), shift_term(S, J1, J0),
    ( I = I0, J = J0 ; I = J0, J = I0 ).

% ----- index translation (induction-variable normalisation) -------------------
% Within a statement that exchanges positions V+c1 and V+c2, every index that is
% affine in V is shifted by -min(c1, c2): swap(i-1, i) == swap(j, j+1).
stmt_shift(S, V, D) :-
    once(raw_exchange(S, _, I, J)), aff(I, V, C1), aff(J, V, C2), D is min(C1, C2), D =\= 0.

aff(var(V), V, 0).
aff(op(add, [var(V), int(C)]), V, C).
aff(op(sub, [var(V), int(K)]), V, C) :- C is -K.

mk_aff(V, 0, var(V)) :- !.
mk_aff(V, C, op(add, [var(V), int(C)])) :- C > 0, !.
mk_aff(V, C, op(sub, [var(V), int(K)])) :- K is -C.

shift_term(S, T0, T) :- stmt_shift(S, V, D), !, shift(V, D, T0, T).
shift_term(_, T, T).

shift(V, D, T0, T) :- aff(T0, V, C), !, C1 is C - D, mk_aff(V, C1, T).
shift(_, _, T, T) :- atomic(T), !.
shift(V, D, T0, T) :- T0 =.. [F|As], maplist(shift(V, D), As, Bs), T =.. [F|Bs].

raw_exchange(S, Q, I, J) :-                      % tuple swap, rotatef, functional rewrite
    par_assign(S, Ts, Vs),
    nth0(A, Ts, elem(Q, I)), nth0(B, Ts, elem(Q2, J)), A < B, Q2 == Q, I \== J,
    nth0(A, Vs, VA), nth0(B, Vs, VB), VA == elem(Q, J), VB == elem(Q, I).
raw_exchange(S, Q, I, J) :-                      % t = q[i]; q[i] = q[j]; q[j] = t
    assign(S1, var(T), elem(Q, I)), next_stmt(S1, S),
    assign(S, elem(Q2, I2), elem(Q3, J)), Q2 == Q, Q3 == Q, I2 == I, I \== J,
    next_stmt(S, S3), assign(S3, elem(Q4, J2), var(T2)), Q4 == Q, J2 == J, T2 == T.
raw_exchange(S, Q, I, J) :-                      % v.swap(i, j), Collections.swap(l, i, j)
    call_at(S, swap, [Q, I, J]), I \== J.
raw_exchange(S, Q, I, J) :-                      % R: x[c(i, j)] <- x[c(j, i)]
    assign(S, elem(Q, call(c, [I, J])), elem(Q2, call(c, [J2, I2]))),
    Q2 == Q, I2 == I, J2 == J, I \== J.

% ----- conditions --------------------------------------------------------------
norm(op(O, [call(F, [A, B]), int(0)]), N) :-    % a.compareTo(b) > 0  ==  a > b
    memberchk(F, [compareTo, compare, cmp]), !, norm(op(O, [A, B]), N).
norm(op(lt, [A, B]), op(gt, [B, A])) :- !.
norm(op(le, [A, B]), op(ge, [B, A])) :- !.
norm(C, C).

negate(op(gt, [A, B]), op(ge, [B, A])) :- !.
negate(op(ge, [A, B]), op(gt, [B, A])) :- !.
negate(op(lt, [A, B]), op(ge, [A, B])) :- !.
negate(op(le, [A, B]), op(gt, [A, B])) :- !.
negate(op(eq, X), op(ne, X)) :- !.
negate(op(ne, X), op(eq, X)) :- !.
negate(op(not, [C]), N) :- !, norm(C, N).
negate(C, op(not, [C])).

flip(true, false).
flip(false, true).

% A negation is pushed into the polarity: not(c)/true == c/false.
norm_pol(op(not, [C]), P0, N, P) :- !, flip(P0, P1), norm_pol(C, P1, N, P).
norm_pol(C, P, N, P) :- norm(C, N).

nguard(S, N, P) :- nguard0(S, N0, P), shift_term(S, N0, N2), elem_iter(S, N2, N1),
    ( N = N1 ; N1 = op(eq, [A, B]), N = op(eq, [B, A]) ).

nguard0(S, N, P) :- guard(S, C, P0), norm_pol(C, P0, N, P).
% Sound consequences over a strict total order (integers):
%   a > b               =>  a \= b  and  not(b > a)
%   not(a > b), not(b > a)  =>  a = b
nguard0(S, op(eq, [A, B]), false) :- guard_pos(S, op(gt, [A, B])).
nguard0(S, op(eq, [B, A]), false) :- guard_pos(S, op(gt, [A, B])).
nguard0(S, op(gt, [B, A]), false) :- guard_pos(S, op(gt, [A, B])).
nguard0(S, op(eq, [A, B]), true) :-
    guard_neg_gt(S, A, B), guard_neg_gt(S, B, A).

guard_pos(S, C) :- guard(S, C0, P0), norm_pol(C0, P0, C, true).
% not(a > b) appears either as gt(a,b)/false or, normalised, as ge(b,a)/true
guard_neg_gt(S, A, B) :- guard(S, C0, P0), norm_pol(C0, P0, C, P),
    ( P == false, C = op(gt, [A, B]) ; P == true, C = op(ge, [B, A]) ).

lcond(L, N) :- loop_cond(L, C), norm_pol(C, true, N0, P),
    ( P == true -> N = N0 ; negate(N0, N1), norm(N1, N) ).

lvar(L, var(N)) :- loop_var(L, N).

% ----- values: copy propagation of single-definition temporaries --------------
value(S, T, V) :- assign(S, T, V0), live(S), stmt_func(S, F), resolve(F, S, V0, V1),
    deep_norm(V1, V2), elem_iter(S, V2, V).
value(S, var(X), V) :-                           % a, b = b, a % b  (non-element targets)
    par_assign(S, Ts, Vs), live(S), nth0(K, Ts, var(X)), nth0(K, Vs, V0),
    deep_norm(V0, V1), elem_iter(S, V1, V).

% ----- G4: for x in s  ->  x is elem(s, x) inside that loop ---------------------
elem_iter(S, T0, T) :-
    findall(X-Q, (loop_iter(L, Q), loop_var(L, X), under(S, L), \+ counting_range(Q)), Ps),
    foldl(elemize, Ps, T0, T).
% an element of range(a, b) / seq_len(n) / [a..b] IS the counter: such a loop is a counting loop
counting_range(call(R, _)) :- memberchk(R, [range, xrange, seq_len, seq, seq_along]).
elemize(X-Q, T0, T) :- T0 == var(X), !, T = elem(Q, var(X)).
elemize(_, T, T) :- atomic(T), !.
elemize(P, T0, T) :- T0 =.. [F|As], maplist(elemize(P), As, Bs), T =.. [F|Bs].

% canonical outputs: returns (and yields) and appends, with element iteration applied
cret(S, V) :- ret(S, V0), live(S), cexpr(S, V0, V1), strip_self(V1, V).

% a recursive call is represented by its parameter updates (value/3), so the
% call's argument order never matters: gcd(b % a, a) == gcd b (a mod b)
strip_self(T, T) :- atomic(T), !.
strip_self(call('$self', _), call('$self', [])) :- !.
strip_self(T0, T) :- T0 =.. [F|As], maplist(strip_self, As, Bs), T =.. [F|Bs].
capp(S, Q, X) :- call_at(S, append, [Q, X0]), live(S), cexpr(S, X0, X).

% copy propagation of a single-definition TEMPORARY (never a parameter: parameter
% updates of a recursive call are simultaneous, never a definition of the same statement)
resolve(F, S, var(X), V) :-
    \+ param(F, _, X),
    findall(D-V0, (assign(D, var(X), V0), stmt_func(D, F)), [D-V0]), D \== S, V0 \= var(_),
    \+ killed(F, D, S, V0), !, V = V0.
resolve(_, _, V, V).

% Reaching definitions (Aho-Sethi-Ullman, approximated by line order and loop
% nesting): the copy D of V0 may replace a use at S only if no operand of V0 is
% redefined on a path from D to S. An operand var(Y) is killed by an assignment
% to Y (or loop variable Y); a sequence Q read as elem(var(Q), _) is killed by an
% element write or exchange on Q. A kill K is on a path D -> S when it lies
% between them in the text, or in a loop around S that does not re-run D.
killed(F, D, S, V0) :-
    stmt(D, F, _, LD), stmt(S, F, _, LS),
    operand(V0, Kind, Y), kill(F, Kind, Y, K, LK), K \== D, \+ exclusive(K, S),
    (   LD < LK, LK < LS                % a statement reads before it writes
    ;   under(S, L), stmt(L, F, _, _), \+ under(D, L), ( K == L ; under(K, L) )
    ), !.
% opposite outcomes of the same test: the two statements never run in one pass
exclusive(K, S) :- guard(K, C, P1), guard(S, C2, P2), C2 == C, P1 \== P2, !.
operand(V0, var, Y) :- sub_term(var(Y), V0), atom(Y).
operand(V0, seq, Q) :- sub_term(elem(var(Q), _), V0), atom(Q).
kill(F, var, Y, K, LK) :- assign(K, var(Y), _), stmt(K, F, _, LK).
kill(F, var, Y, K, LK) :- par_assign(K, Ts, _), memberchk(var(Y), Ts), stmt(K, F, _, LK).
kill(F, var, Y, L, LL) :- loop_var(L, Y), stmt(L, F, _, LL).
kill(F, seq, Q, K, LK) :- assign(K, elem(var(Q), _), _), stmt(K, F, _, LK).
kill(F, seq, Q, K, LK) :- par_assign(K, Ts, _), memberchk(elem(var(Q), _), Ts), stmt(K, F, _, LK).
kill(F, seq, Q, K, LK) :- call_at(K, Fn, [var(Q)|_]), memberchk(Fn, [swap, append, pop, insert, remove]),
    stmt(K, F, _, LK).

% Two spellings of the same midpoint: lo + (hi - lo) / 2  ==  (lo + hi) / 2
canon_expr(op(add, [L, op(div, [op(sub, [H, L2]), int(2)])]), op(div, [op(add, [L, H]), int(2)])) :-
    L2 == L, !.
canon_expr(op(shr, [X, int(1)]), op(div, [X, int(2)])) :- !.     % (lo + hi) >>> 1
canon_expr(V, V).

% Deep normal form of an expression: comparisons point the same way everywhere.
deep_norm(T, T) :- atomic(T), !.
deep_norm(op(lt, [A, B]), op(gt, [B1, A1])) :- !, deep_norm(A, A1), deep_norm(B, B1).
deep_norm(op(le, [A, B]), op(ge, [B1, A1])) :- !, deep_norm(A, A1), deep_norm(B, B1).
deep_norm(T0, T) :- T0 =.. [F|As], maplist(deep_norm, As, Bs), T1 =.. [F|Bs], canon_expr(T1, T).

% Forward substitution of single-definition locals (SSA copy/expression propagation):
% `lesser = filter(...); f(lesser)` == `f(filter(...))`. Bounded depth, never params
% or loop variables, never a self-referencing definition.
% inline/3 has no use site, so it is refused if ANY use of X can see a kill
killed_any_use(F, D, X, V0) :-
    stmt(S, F, _, _), S \== D, uses_var(S, X), killed(F, D, S, V0), !.
uses_var(S, X) :- ( assign(S, T, V) ; ret(S, V), T = none ; call_at(S, _, V), T = none
                  ; guard(S, V, _), T = none ; loop_cond(S, V), T = none ),
    ( sub_term(var(Y), V) ; T \= none, sub_term(var(Y), T) ), Y == X, !.
inline(F, T0, T) :- inline(F, 3, T0, T).
inline(_, 0, T, T) :- !.
inline(F, D, var(X), T) :-
    \+ param(F, _, X), \+ (loop_var(L, X), loop(L, F, _)),
    findall(D0-V0, (assign(D0, var(X), V0), stmt_func(D0, F)), [D0-V0]),
    \+ (sub_term(var(Y), V0), Y == X), \+ killed_any_use(F, D0, X, V0), !,
    D1 is D - 1, inline(F, D1, V0, T).
inline(_, _, T, T) :- atomic(T), !.
inline(_, _, T, T) :- T = var(_), !.
inline(F, D, T0, T) :- T0 =.. [Fn|As], maplist(inline(F, D), As, Bs), T =.. [Fn|Bs].

cexpr(S, T0, T) :- stmt_func(S, F), inline(F, T0, T1), deep_norm(T1, T2), elem_iter(S, T2, T).

% ----- nesting, also across calls (SDG, Horwitz-Reps-Binkley) ------------------
under(X, L) :- in_loop(X, L).
under(X, L) :-
    stmt_func(X, G), func(G, GName, _), base_name(GName, Base),
    call_at(C, Base, _), stmt_func(C, F2), F2 \== G, under(C, L).
% the call site itself may be the loop statement (e.g. a loop header)
under(X, L) :-
    stmt_func(X, G), func(G, GName, _), base_name(GName, Base),
    call_at(L, Base, _), loop(L, F2, _), F2 \== G.

base_name(Name, Base) :-
    atomic_list_concat(Parts, '.', Name), last(Parts, Last),
    ( sub_atom(Last, B, _, _, '/') -> sub_atom(Last, 0, B, _, Base) ; Base = Last ).

% functions reachable from F through calls (F included)
reaches(F, F).
reaches(F, G) :- reach_step(F, G0), reaches(G0, G).
reach_step(F, G) :- call_at(C, Name, _), stmt_func(C, F), func(G, GName, _), G \== F,
    base_name(GName, Name).

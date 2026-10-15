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

nguard(S, N, P) :- nguard0(S, N0, P), shift_term(S, N0, N1),
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
value(S, T, V) :- assign(S, T, V0), live(S), stmt_func(S, F), resolve(F, V0, V1), canon_expr(V1, V).

resolve(F, var(X), V) :-
    findall(V0, (assign(D, var(X), V0), stmt_func(D, F)), [V0]), V0 \= var(_), !, V = V0.
resolve(_, V, V).

% Two spellings of the same midpoint: lo + (hi - lo) / 2  ==  (lo + hi) / 2
canon_expr(op(add, [L, op(div, [op(sub, [H, L2]), int(2)])]), op(div, [op(add, [L, H]), int(2)])) :-
    L2 == L, !.
canon_expr(op(shr, [X, int(1)]), op(div, [X, int(2)])) :- !.     % (lo + hi) >>> 1
canon_expr(V, V).

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

/* v0.2 (doc 03): the C that ECL compiles from Common Lisp, as AP13 language-neutral facts.

   The AP13 C lowerer (unchanged) lowered ECL's C; ecl_facts.py turned every label into the
   statement ecl_label(N) and every goto into ecl_goto(N). This file rewrites the base facts of
   each function, after loading and before the AP13 rules run (as family_main.pl does for Lisp
   accessors), so that roles.pl and families.pl trace them with the same rules as any language:

     1. operator table   ECL runtime calls -> neutral terms (ecl_minus -> op(sub), aref -> elem)
     2. blocks           symbolic execution of each basic block (local value numbering): ECL's
                         temporaries are replaced by their values; the writes of one block become
                         assignments, or ONE parallel assignment when a later write reads a value
                         an earlier write of the block replaced (psetq, shiftf, rotatef)
     3. loops            a goto back to an earlier label is a loop (natural loop of a CFG back
                         edge); its exit test gives loop_cond, the counter it tests loop_var
     4. branches         a forward conditional goto guards the statements it jumps over (then)
                         and, when the then-part ends with a jump past the target, the statements
                         between target and that jump (else): control dependence
     5. recursion        a self-call carries its parameter updates, as the AP13 lowerers emit

   Assumptions (documented, doc 03): a two-argument call of a function object (funcall of a
   comparator parameter) is read as a < b; a Lisp variable is ECL's v<k><name>, every other
   variable (T<k>, v<k>, value0, env0) is a compiler temporary.
*/
:- dynamic ecl_unresolved/2, ecl_lispvar/2.

% ----- 1. operator table -----------------------------------------------------------------
ecl_bin(ecl_plus, add).          ecl_bin(ecl_minus, sub).          ecl_bin(ecl_times, mul).
ecl_bin(ecl_divide, div).        ecl_bin(ecl_floor2, div).         ecl_bin(ecl_truncate2, div).
ecl_bin(ecl_rem, mod).           ecl_bin(ecl_lower, lt).           ecl_bin(ecl_lowereq, le).
ecl_bin(ecl_greater, gt).        ecl_bin(ecl_greatereq, ge).       ecl_bin(ecl_number_equalp, eq).
ecl_bin(ecl_eql, eq).            ecl_bin(ecl_equal, eq).           ecl_bin(ecl_eq, eq).
ecl_box(F) :- memberchk(F, [ecl_make_fixnum, ecl_fixnum, ecl_make_integer, ecl_to_fixnum, ecl_make_bool,
                            ecl_to_bool, ecl_make_int, ecl_to_int, ecl_make_cint]).
ecl_aref(F) :- memberchk(F, [ecl_aref_unsafe, ecl_aref1, ecl_aref, ecl_elt, ecl_char]).
ecl_aset(F) :- memberchk(F, [ecl_aset_unsafe, ecl_aset1, ecl_aset, ecl_elt_set, ecl_char_set]).

ecl_op(call(F, [A, B]), op(O, [A, B])) :- ecl_bin(F, O), !.
ecl_op(call(F, [X]), X) :- ecl_box(F), !.
ecl_op(call(F, [Q, I]), elem(Q, I)) :- ecl_aref(F), !.
ecl_op(call(ecl_one_plus, [X]), op(add, [X, int(1)])) :- !.
ecl_op(call(ecl_one_minus, [X]), op(sub, [X, int(1)])) :- !.
ecl_op(call(ecl_zerop, [X]), op(eq, [X, int(0)])) :- !.
ecl_op(call(ecl_minusp, [X]), op(lt, [X, int(0)])) :- !.
ecl_op(call(ecl_plusp, [X]), op(gt, [X, int(0)])) :- !.
ecl_op(call(ecl_oddp, [X]), op(ne, [op(mod, [X, int(2)]), int(0)])) :- !.
ecl_op(call(ecl_evenp, [X]), op(eq, [op(mod, [X, int(2)]), int(0)])) :- !.
ecl_op(call(ecl_negate, [X]), op(neg, [X])) :- !.
ecl_op(call(ecl_length, [X]), call(len, [X])) :- !.
ecl_op(call(ecl_number_compare, [A, B]), call(compare, [A, B])) :- !.
ecl_op(call(ecl_car, [X]), elem(X, int(0))) :- !.
ecl_op(call(ecl_cdr, [X]), tail(X, 1)) :- !.
ecl_op(call(ecl_cons, [A, B]), cons(A, B)) :- !.
ecl_op(call(ecl_list1, [X]), list([X])) :- !.
ecl_op(call('Null', [X]), op(not, [X])) :- !.
ecl_op(call(ecl_funcall, [_, A, B]), op(lt, [A, B])) :- !.      % comparator: ascending assumed
ecl_op(var('ECL_NIL'), bool(false)) :- !.
ecl_op(var('ECL_T'), bool(true)) :- !.
ecl_op(var(V), var(N)) :- lisp_name(V, N), !.

% ECL names a Lisp variable v<k><name> (v2b, v4lo); temporaries are T<k>, v<k>, value0, env0
lisp_name(V, N) :- atom(V), \+ ecl_temp(V), atom_codes(V, [0'v|Cs]), Cs = [D|_], code_type(D, digit),
    drop_digits(Cs, Ns), Ns = [C|_], \+ code_type(C, digit), atom_codes(N, Ns).
drop_digits([D|Cs], Ns) :- code_type(D, digit), !, drop_digits(Cs, Ns).
drop_digits(Ns, Ns).
ecl_temp(X) :- memberchk(X, [value0, env0, cl_env_copy]), !.
ecl_temp(X) :- atom_codes(X, [C|Ds]), memberchk(C, [0'T, 0'v]), Ds = [D|_], code_type(D, digit),
    drop_digits(Ds, Rest), ( Rest == [] ; Rest = [0'_|Ks], Ks \== [], drop_digits(Ks, []) ).   % v8, v8_1 (scoped)
lisp_var(F, X) :- ( \+ ecl_temp(X) ; ecl_lispvar(F, X) ), !.

ecl_term(T, T) :- \+ compound(T), !.
ecl_term(T0, T) :- T0 =.. [F|As], maplist(ecl_term, As, Bs), T1 =.. [F|Bs], ecl_top(T1, T).
ecl_top(T1, T) :- ecl_op(T1, T2), T2 \== T1, !, ecl_top(T2, T).
ecl_top(T, T).

% ----- events: the statements of one function in source order --------------------------------
stmt_order(F, Ss) :-
    findall(L-N-S, ( stmt(S, F, K, L), K \== loop, sub_atom(S, 1, _, 0, NA), atom_number(NA, N) ), Ks),
    msort(Ks, Sorted), findall(S, member(_-_-S, Sorted), Ss).

event(S, label(N)) :- call_at(S, ecl_label, [int(N)]), !.
event(S, goto(N, C, P)) :- call_at(S, ecl_goto, [int(N)]), !,
    ( guard(S, C0, P) -> ecl_term(C0, C) ; C = none, P = none ).
event(S, drop) :- guard(S, C, _), sub_term(U, C), compound(U), U = call(ecl_unlikely, _), !.
event(S, ret(V)) :- stmt(S, _, ret, _), ret(S, V0), !, ecl_term(V0, V).
event(S, write(T, V)) :- stmt(S, _, assign, _), assign(S, T0, V0), T0 \= other(_), !,
    ecl_term(T0, T), ecl_term(V0, V).
event(S, write(elem(Q, I), V)) :- stmt(S, _, call, _), call_at(S, Fn, [Q0, I0, V0]), ecl_aset(Fn), !,
    ecl_term(elem(Q0, I0), elem(Q, I)), ecl_term(V0, V).
event(S, call(Fn, As)) :- stmt(S, _, call, _), call_at(S, Fn0, As0), \+ boiler_call(Fn0), !,
    ecl_term(call(Fn0, As0), T), ( T = call(Fn, As) -> true ; Fn = expr, As = [T] ).
event(_, drop).
boiler_call(F) :- memberchk(F, [ecl_cs_check, ecl_process_env, ecl_label, ecl_goto]), !.
boiler_call(F) :- ( sub_atom(F, 0, _, _, 'FE') ; sub_atom(F, 0, _, _, ecl_stack_frame)
                  ; sub_atom(F, 0, _, _, ecl_bds) ; sub_atom(F, 0, _, _, ecl_frs) ), !.

events(F, Evs) :- stmt_order(F, Ss),
    findall(ev(S, L, E), ( member(S, Ss), stmt(S, F, _, L), event(S, E), E \== drop ), Evs).

% ----- stable temporaries: one definition, value fixed for the whole function -----------------
stable_env(F, Evs, Env) :-
    findall(X-V, ( member(ev(_, _, write(var(X), V)), Evs), ecl_temp(X), \+ ecl_lispvar(F, X) ), Ds),
    findall(X-V, ( member(X-V, Ds), aggregate_all(count, member(X-_, Ds), 1) ), Single),
    findall(Y, changed(F, Evs, Y), Ch0), sort(Ch0, Changed),
    stable_close(Single, Changed, [], Env0), list_to_assoc(Env0, Env).
% a variable whose value changes after it is first set: a parameter written, a variable written
% twice, or a sequence whose elements are written
changed(F, Evs, Y) :- member(ev(_, _, write(var(Y), _)), Evs), lisp_var(F, Y),
    ( param(F, _, P0), ecl_term(var(P0), var(P)), P == Y
    ; aggregate_all(count, member(ev(_, _, write(var(Y), _)), Evs), N), N >= 2 ).
changed(_, Evs, Q) :- member(ev(_, _, write(elem(var(Q), _), _)), Evs).
stable_close(Single, Changed, Acc, Env) :-
    (   member(X-V, Single), \+ memberchk(X-_, Acc), fixed(V, Changed, Acc)
    ->  list_to_assoc(Acc, A), empty_assoc(E), subst(none, A, E, V, V1),
        stable_close(Single, Changed, [X-V1|Acc], Env)
    ;   Env = Acc ).
fixed(V, Changed, Acc) :-
    \+ ( sub_term(var(Y), V), memberchk(Y, Changed) ),
    \+ ( sub_term(E, V), compound(E), E = elem(var(Q), _), memberchk(Q, Changed) ),
    \+ ( sub_term(var(T), V), ecl_temp(T), \+ memberchk(T-_, Acc) ),
    \+ ( sub_term(C, V), compound(C), C = call('$self', _) ).

% ----- 2. symbolic execution of basic blocks --------------------------------------------------
% st(Env, Elems, Pending): values of variables in the block (in block-entry terms), element
% writes of the block, and the block's writes not yet emitted.
subst(F, Env, Elems, T0, T) :- subst_(F, Env, Elems, T0, T).
subst_(_, _, _, T, T) :- \+ compound(T), !.
subst_(F, Env, _, var(X), T) :- !,
    ( get_assoc(X, Env, V) -> T = V
    ; T = var(X), ( F \== none, ecl_temp(X), \+ ecl_lispvar(F, X) -> assertz(ecl_unresolved(F, X)) ; true ) ).
subst_(F, Env, Elems, elem(Q0, I0), T) :- !, subst_(F, Env, Elems, Q0, Q), subst_(F, Env, Elems, I0, I),
    ( member(E-V, Elems), E == elem(Q, I) -> T = V ; T = elem(Q, I) ).
subst_(F, Env, Elems, T0, T) :- T0 =.. [Fn|As], maplist(subst_(F, Env, Elems), As, Bs), T =.. [Fn|Bs].

% symex(F, Evs, Stable, Items): items it(S, Line, What) in source order;
% What = label(N) | goto(N, C, P) | st(Kind, Facts)
symex(F, Evs, Stable, Items) :- symex(Evs, F, Stable, st(Stable, [], []), Items).
symex([], F, _, St, Items) :- flush(F, St, _, Items, []).
symex([ev(S, L, E)|Evs], F, Stable, St0, Items) :- step(E, S, L, F, Stable, St0, St, Items, Rest),
    symex(Evs, F, Stable, St, Rest).

step(write(var(X), V0), S, L, F, _, st(Env0, El, P), st(Env, El, P1), Items, Items) :- !,
    subst(F, Env0, El, V0, V), put_assoc(X, Env0, V, Env),
    ( lisp_var(F, X) -> append(P, [w(S, L, var(X), V)], P1) ; P1 = P ).
step(write(elem(Q0, I0), V0), S, L, F, _, st(Env, El0, P), st(Env, [elem(Q, I)-V|El1], P1), Items, Items) :- !,
    subst(F, Env, El0, Q0, Q), subst(F, Env, El0, I0, I), subst(F, Env, El0, V0, V),
    exclude(same_key(elem(Q, I)), El0, El1), append(P, [w(S, L, elem(Q, I), V)], P1).
step(label(N), S, L, F, Stable, St, st(Stable, [], []), Items, Rest) :- !,
    flush(F, St, _, Items, [it(S, L, label(N))|Rest]).
step(goto(N, C0, P), S, L, F, Stable, St, st(Stable, [], []), Items, Rest) :- !,
    flush(F, St, Env, Items, [it(S, L, goto(N, C, P))|Rest]), ( C0 == none -> C = none ; subst(F, Env, [], C0, C) ).
step(ret(V0), S, L, F, Stable, St, st(Stable, [], []), Items, Rest) :- !,
    flush(F, St, Env, Items, [it(S, L, st(ret, [ret(S, V)]))|Rest]), subst(F, Env, [], V0, V).
step(call(Fn, As0), S, L, F, _, St, st(Env, [], []), Items, Rest) :-
    flush(F, St, Env, Items, [it(S, L, st(call, [call_at(S, Fn, As)]))|Rest]), subst(F, Env, [], As0, As).
same_key(K, E-_) :- E == K.

% flush: emit the pending writes; afterwards variables hold their new values, so the block's
% environment keeps only temporaries whose values do not read a replaced target
flush(_, st(Env, _, []), Env, Items, Items) :- !.
flush(_, st(Env0, _, P0), Env, Items, Rest) :-
    last_writes(P0, P),
    findall(T, member(w(_, _, T, _), P), Ts),
    (   parallel(P)
    ->  P = [w(S1, L1, _, _)|_], findall(V, member(w(_, _, _, V), P), Vs),
        Items = [it(S1, L1, st(assign, [par_assign(S1, Ts, Vs)]))|Rest]
    ;   findall(it(S, L, st(assign, [assign(S, T, V)])), member(w(S, L, T, V), P), Ws), append(Ws, Rest, Items)
    ),
    findall(V-cur(T), ( member(w(_, _, T, V), P), T = var(_) ), News),
    assoc_to_list(Env0, KVs),
    findall(X-V, ( member(X-V0, KVs), ecl_temp(X), current_terms(News, V0, V1),
                   \+ ( member(T, Ts), old_read(V1, T) ), uncur(V1, V) ), Keep),
    list_to_assoc(Keep, Env).
% a value just written is now the variable that holds it: t = q[(lo + hi) / 2] after
% mid = (lo + hi) / 2 reads q[mid]; any other read of a replaced target drops the temporary
current_terms(News, V0, V) :- member(N-T, News), N == V0, !, V = T.
current_terms(_, V, V) :- \+ compound(V), !.
current_terms(News, V0, V) :- V0 =.. [F|As], maplist(current_terms(News), As, Bs), V =.. [F|Bs].
old_read(V, T) :- V == T, !.
old_read(V, T) :- compound(V), V \= cur(_), arg(_, V, A), old_read(A, T), !.
uncur(cur(T), T) :- !.
uncur(V, V) :- \+ compound(V), !.
uncur(V0, V) :- V0 =.. [F|As], maplist(uncur, As, Bs), V =.. [F|Bs].
% a target written twice in one block keeps its last write
last_writes(P0, P) :- reverse(P0, R0), first_per_target(R0, [], R), reverse(R, P).
first_per_target([], _, []).
first_per_target([W|Ws], Seen, Out) :- W = w(_, _, T, _),
    ( member(T2, Seen), T2 == T -> Out = Rest ; Out = [W|Rest] ), first_per_target(Ws, [T|Seen], Rest).
parallel(P) :- nth1(K, P, w(_, _, _, V)), nth1(J, P, w(_, _, T, _)), J < K, sub_term(T2, V), T2 == T, !.

% ----- 3./4. loops and branches over the item list --------------------------------------------
% positions are item indices; label N at position B and a goto to N at G >= B: loop [B, G]
label_pos(Items, N, B) :- nth1(B, Items, it(_, _, label(N))), !.
goto_at(Items, G, N, C, P, T) :- nth1(G, Items, it(_, _, goto(N, C, P))), label_pos(Items, N, T).
loops(Items, Loops) :-
    findall(T, ( goto_at(Items, G, _, _, _, T), T =< G ), Ts0), sort(Ts0, Ts),
    findall(lp(T, G), ( member(T, Ts), aggregate_all(max(G0), ( goto_at(Items, G0, _, _, _, T1), T1 == T, T =< G0 ), G) ), Loops).
inside(I, lp(B, G)) :- B =< I, I =< G.
innermost(Loops, I, Lp) :-
    findall(W-lp(B, G), ( member(lp(B, G), Loops), inside(I, lp(B, G)), W is G - B ), Ws), msort(Ws, [_-Lp|_]).
exit_goto(Items, Loops, I, Lp) :- goto_at(Items, I, _, _, _, T), innermost(Loops, I, Lp), \+ inside(T, Lp).
% a conditional goto that only skips exits of its loop is the loop's test
loop_test(Items, Loops, I) :-
    goto_at(Items, I, _, C, _, T), C \== none, T > I, innermost(Loops, I, Lp), inside(T, Lp),
    I1 is I + 1, T1 is T - 1, I1 =< T1,
    forall(between(I1, T1, K), exit_goto(Items, Loops, K, Lp)).

% guards of the statements at position K from the branches around it
branch_guard(Items, Loops, K, C, Pol) :-
    goto_at(Items, I, _, C, P, T), C \== none, T > I, \+ loop_test(Items, Loops, I),
    ( innermost(Loops, I, lp(_, G)), T > G -> End is G + 1 ; End = T ),
    (   I < K, K < End, flip(P, Pol)
    ;   T1 is T - 1, nth1(T1, Items, it(_, _, goto(_, none, none))), goto_at(Items, T1, _, _, _, T2), T2 > T,
        ( innermost(Loops, I, lp(_, G2)), T2 > G2 -> End2 is G2 + 1 ; End2 = T2 ),
        T < K, K < End2, Pol = P
    ).

% continuation condition of a loop from its exit: preferably the test just before the back edge
loop_cont(Items, Loops, lp(B, G), Cont) :-
    findall(X, ( between(B, G, X), exit_item(Items, Loops, X, lp(B, G)) ), Xs),
    G1 is G - 1, ( memberchk(G1, Xs) -> Order = [G1|Xs] ; Order = Xs ),
    member(X, Order), exit_cont(Items, Loops, X, Cont), !.
exit_item(Items, Loops, X, Lp) :- exit_goto(Items, Loops, X, Lp1), Lp1 == Lp.
exit_item(Items, Loops, X, Lp) :- nth1(X, Items, it(_, _, st(ret, _))), innermost(Loops, X, Lp1), Lp1 == Lp.
exit_cont(Items, _, X, Cont) :- goto_at(Items, X, _, C, P, _), C \== none, !, cont_when_not(C, P, Cont).
exit_cont(Items, Loops, X, Cont) :- X0 is X - 1, loop_test(Items, Loops, X0), !,
    goto_at(Items, X0, _, C, P, _), holds(C, P, Cont).
exit_cont(Items, Loops, X, Cont) :- branch_guard(Items, Loops, X, C, P), !, cont_when_not(C, P, Cont).
holds(C, true, C).
holds(C, false, op(not, [C])).
cont_when_not(C, true, op(not, [C])).
cont_when_not(C, false, C).

% the counter the loop condition tests and the body steps by a constant
loop_counter(Facts, Cont, X) :-
    sub_term(V, Cont), compound(V), V = var(X), member(assign(_, var(X2), op(O, [var(X3), int(_)])), Facts),
    X2 == X, X3 == X, memberchk(O, [add, sub]), !.

% ----- assembling the new facts of one function ---------------------------------------------
ecl_function(F) :-
    retractall(ecl_unresolved(F, _)), events(F, Evs),
    stable_env(F, Evs, Stable0), symex(F, Evs, Stable0, _),
    forall(ecl_unresolved(F, X), ( ecl_lispvar(F, X) -> true ; assertz(ecl_lispvar(F, X)) )),
    stable_env(F, Evs, Stable), symex(F, Evs, Stable, Items),
    loops(Items, Loops),
    findall(Fact, item_fact(F, Items, Loops, Fact), Facts0),
    recursion_facts(F, Facts0, Facts),
    retract_function(F), forall(member(Fa, Facts), assertz(Fa)).

item_fact(F, Items, Loops, Fact) :-
    nth1(K, Items, it(S, L, What)),
    (   What = st(Kind, Fs) -> stmt_facts(F, Items, Loops, K, S, L, Kind, Fs, Fact)
    ;   What = label(_), member(Lp, Loops), Lp = lp(K, _) -> loop_facts(F, Items, Loops, Lp, S, L, Fact)
    ).
stmt_facts(F, Items, Loops, K, S, L, Kind, Fs, Fact) :-
    (   Fact = stmt(S, F, Kind, L)
    ;   member(Fact, Fs)
    ;   branch_guard(Items, Loops, K, C, P), Fact = guard(S, C, P)
    ;   enclosing(Items, Loops, K, LS), Fact = in_loop(S, LS)
    ;   next_item(Items, Loops, K, S2), Fact = next_stmt(S, S2)
    ).
loop_facts(F, Items, Loops, Lp, S, L, Fact) :-
    Lp = lp(B, G),
    (   Fact = stmt(S, F, loop, L)
    ;   Fact = loop(S, F, cond)
    ;   loop_cont(Items, Loops, Lp, C), Fact = loop_cond(S, C)
    ;   loop_cont(Items, Loops, Lp, C), findall(A, ( between(B, G, K), nth1(K, Items, it(_, _, st(_, Fs))), member(A, Fs) ), As),
        loop_counter(As, C, X), Fact = loop_var(S, X)
    ;   branch_guard(Items, Loops, B, C, P), Fact = guard(S, C, P)
    ;   enclosing(Items, Loops, B, LS), LS \== S, Fact = in_loop(S, LS)
    ;   next_item(Items, Loops, B, S2), Fact = next_stmt(S, S2)
    ).
% every loop around position K (its label statement is the loop statement)
enclosing(Items, Loops, K, LS) :- member(lp(B, G), Loops), inside(K, lp(B, G)), K \== B,
    nth1(B, Items, it(LS, _, _)).
% the next statement at the same nesting (an inner loop counts as one statement)
next_item(Items, Loops, K, S2) :-
    nesting(Loops, K, N0), length(Items, Len), K1 is K + 1,
    between(K1, Len, J), nth1(J, Items, it(S2, _, W)), stmt_item(Loops, J, W), nesting(Loops, J, N0), !.
stmt_item(_, _, st(_, _)).
stmt_item(Loops, J, label(_)) :- memberchk(lp(J, _), Loops).
nesting(Loops, K, N) :- findall(B, ( member(lp(B, G), Loops), inside(K, lp(B, G)), K \== B ), N).

% ----- 5. recursion: self-calls carry their parameter updates ---------------------------------
recursion_facts(F, Facts0, Facts) :-
    findall(S-Args, ( member(Fa, Facts0), fact_stmt(Fa, S), sub_term(C, Fa), compound(C), C = call('$self', Args) ), SA0),
    sort(SA0, SA),
    findall(Fa, ( member(S-Args, SA), self_fact(F, S, Args, Fa) ), New),
    (   SA = [S1-_|_], loop(LR, F, recursion)
    ->  findall(in_loop(S, LR), ( member(Fa, Facts0), ( Fa = ret(S, _) ; Fa = call_at(S, '$self', _) ; member(S-_, SA) ) ), In0),
        sort(In0, In),
        ( member(guard(S1, C, P), Facts0) -> holds(C, P, Cont), Rc = [loop_cond(LR, Cont)] ; Rc = [] ),
        append([Facts0, New, In, Rc], Facts)
    ;   append(Facts0, New, Facts)
    ).
fact_stmt(assign(S, _, _), S).
fact_stmt(par_assign(S, _, _), S).
fact_stmt(ret(S, _), S).
fact_stmt(call_at(S, _, _), S).
self_fact(_, S, Args, call_at(S, '$self', Args)).
self_fact(F, S, Args, assign(S, var(P), A)) :- nth0(K, Args, A), param(F, K, P0), ecl_term(var(P0), var(P)), A \== var(P).

% the old facts of F go; the lowerer's recursion loop statement stays
retract_function(F) :-
    findall(S, ( stmt(S, F, K, _), \+ ( K == loop, loop(S, F, recursion) ) ), Ss),
    forall(member(S, Ss), ( retractall(stmt(S, _, _, _)), retractall(guard(S, _, _)), retractall(assign(S, _, _)),
                            retractall(par_assign(S, _, _)), retractall(ret(S, _)), retractall(call_at(S, _, _)),
                            retractall(in_loop(S, _)), retractall(next_stmt(S, _)), retractall(next_stmt(_, S)),
                            retractall(loop(S, _, _)), retractall(loop_var(S, _)), retractall(loop_cond(S, _)),
                            retractall(loop_iter(S, _)) )),
    forall(loop(LR, F, recursion), ( retractall(in_loop(_, LR)), retractall(loop_cond(LR, _)) )).

% compiled function L<k><name> is the Lisp function <name>; parameters lose ECL's v<k> prefix
% (a top-level form, compiled as ecl_toplevel by ecl_compile.py, is <toplevel> as in the AP13 lowerers)
rename_function(F) :-
    func(F, N0, Line), atom_codes(N0, [0'L|Cs]), drop_digits(Cs, Ns), Ns \== [], !,
    atom_codes(N1, Ns), ( N1 == ecl_toplevel -> N = '<toplevel>' ; N = N1 ),
    retract(func(F, N0, Line)), assertz(func(F, N, Line)),
    forall(retract(param(F, K, P0)), ( ecl_term(var(P0), var(P)), assertz(param(F, K, P)) )).
rename_function(_).

ecl_normalise :- forall(func(F, _, _), ecl_function(F)), forall(func(F, _, _), rename_function(F)).

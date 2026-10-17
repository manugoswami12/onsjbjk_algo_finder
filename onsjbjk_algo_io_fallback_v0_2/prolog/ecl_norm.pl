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
:- dynamic ecl_unresolved/2, ecl_lispvar/2, tail_loop/1.

% ----- 1. operator table -----------------------------------------------------------------
% Every row is checked against its definition in ECL's headers (/usr/include/ecl, ECL 21.2.1;
% doc 03 section 8): fixed-arity functions take their arguments, cl_ functions declared
% _ECL_ARGS((cl_narg narg, ...)) take the argument count first. Operator names are AP13's shared
% vocabulary (polyglot_logic/tools/lang_tables.py OPERATORS; Common Lisp '/' is div there too).
ecl_bin(ecl_plus, add).          ecl_bin(ecl_minus, sub).          ecl_bin(ecl_times, mul).
ecl_bin(ecl_divide, div).        ecl_bin(ecl_floor2, div).         ecl_bin(ecl_truncate2, div).
ecl_bin(ecl_rem, mod).           ecl_bin(ecl_lower, lt).           ecl_bin(ecl_lowereq, le).
ecl_bin(ecl_greater, gt).        ecl_bin(ecl_greatereq, ge).       ecl_bin(ecl_number_equalp, eq).
ecl_bin(ecl_eql, eq).            ecl_bin(ecl_equal, eq).
ecl_box(F) :- memberchk(F, [ecl_make_fixnum, ecl_fixnum, ecl_make_integer, ecl_to_fixnum, ecl_make_bool,
                            ecl_to_bool, ecl_make_int, ecl_to_int]).
ecl_aref(F) :- memberchk(F, [ecl_aref_unsafe, ecl_aref1, ecl_aref, ecl_elt, ecl_char, cl_char, cl_schar, cl_elt]).
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
ecl_op(call(F, [X]), elem(X, int(0))) :- memberchk(F, [ecl_car, '_ecl_car', 'ECL_CONS_CAR', cl_car, cl_first]), !.
ecl_op(call(F, [X]), tail(X, 1)) :- memberchk(F, [ecl_cdr, '_ecl_cdr', 'ECL_CONS_CDR', cl_cdr, cl_rest]), !.
ecl_op(call(F, [X]), elem(X, int(1))) :- memberchk(F, [ecl_cadr, cl_cadr, cl_second]), !.
ecl_op(call(F, [A, B]), cons(A, B)) :- memberchk(F, [ecl_cons, 'CONS', cl_cons]), !.
ecl_op(call(ecl_list1, [X]), list([X])) :- !.
ecl_op(call(cl_list, [int(_)|As]), list(As)) :- !.
ecl_op(call(ecl_endp, [X]), op(not, [X])) :- !.                  % (endp l): l is empty
ecl_op(call(coerce_to_list, [X]), X) :- !.                      % si::coerce-to-list: the same sequence
ecl_op(op(add, [int(0), X]), X) :- !.                            % 0 + x
ecl_op(elem(Q, op(add, [op(mul, [I, call(ecl_array_dimension, [Q2, int(1)])]), J])), elem(elem(Q, I), J)) :-
    Q2 == Q, !.                                                      % row-major index of (aref m i j)
ecl_op(call(F, [int(_), A, B|Cs]), T) :- chain(F, O), !, chain_term(O, [A, B|Cs], T).   % (< a b c): a<b, b<c
ecl_op(call(ecl_apply, [call(ecl_symbol, [var(list)])|Vs]), list(Vs)) :- !.   % (multiple-value-list ...)
ecl_op(elem(list(Xs), int(K)), X) :- nth0(K, Xs, X), !.                % car / cadr of a known list
ecl_op(tail(list([_|Xs]), 1), list(Xs)) :- !.
ecl_op(call(cl_mapcar, [int(_), Fn, Q|Qs]), map(Q, Fn, Qs)) :- !.      % (mapcar f q ...): AP13's map term
ecl_op(call(cl_map, [int(_), _, Fn, Q|Qs]), map(Q, Fn, Qs)) :- !.      % (map type f q ...)
ecl_op(call(F, [int(_), Q, I]), elem(Q, I)) :- memberchk(F, [cl_bit, cl_sbit, cl_aref]), !.   % (bit v i), (aref v i)
ecl_op(call(cl_aref, [int(_), Q, I|Is]), E) :- Is \== [], !, foldl([J, E0, elem(E0, J)]>>true, [I|Is], Q, E).   % (aref m i j)
ecl_op(call('Null', [X]), op(not, [X])) :- !.
ecl_op(call(ecl_funcall, [fn(Op), A, B]), op(Op, [A, B])) :- !.  % (funcall #'* a b): the known function
% Common Lisp library functions; ECL passes the argument count first to the variadic cl_ ones
ecl_op(call(F, [X]), call(reverse, [X])) :- memberchk(F, [cl_reverse, cl_nreverse]), !.
ecl_op(call(F, [int(_), A, B|_]), op(eq, [A, B])) :- memberchk(F, [cl_stringE, cl_string_equal]), !.
ecl_op(call(F, [A, B]), op(eq, [A, B])) :- memberchk(F, [cl_equal, cl_equalp]), !.
ecl_op(call(F, [int(_)|As]), concat(As)) :- memberchk(F, [cl_nconc, cl_append]), !.
ecl_op(call(F, [int(_), _, Q|_]), filter(Q, other(predicate))) :-
    memberchk(F, [cl_remove, cl_remove_if, cl_remove_if_not, cl_delete, cl_delete_if, cl_delete_if_not]), !.
ecl_op(call(F, As), call(N, As)) :- compiled_name(F, N), !.     % L2helper(x) / LC1pivot(x): helper, pivot
ecl_op(call(ecl_function, [var(N)]), fn(N)) :- !.                % #'* as an object: fn(mul)
ecl_op(var('ECL_NIL'), bool(false)) :- !.
ecl_op(var('ECL_T'), bool(true)) :- !.
ecl_op(var(V), var(N)) :- lisp_name(V, N), !.

% ECL names a Lisp variable v<k><name> (v2b, v4lo); temporaries are T<k>, v<k>, value0, env0
chain(cl_L, lt). chain(cl_LE, le). chain(cl_G, gt). chain(cl_GE, ge). chain(cl_E, eq).
chain_term(O, [A, B], op(O, [A, B])) :- !.
chain_term(O, [A, B|Cs], op(and, [op(O, [A, B]), T])) :- chain_term(O, [B|Cs], T).
compiled_name(F, N) :- atom(F), atom_codes(F, [0'L|Cs0]), ( Cs0 = [0'C|Cs] -> true ; Cs = Cs0 ),
    Cs = [D|_], code_type(D, digit), drop_digits(Cs, Ns), Ns \== [], atom_codes(N, Ns).
lisp_name(V, N) :- atom(V), \+ ecl_temp(V), atom_codes(V, [0'v|Cs]), Cs = [D|_], code_type(D, digit),
    drop_digits(Cs, Ns), Ns = [C|_], \+ code_type(C, digit), atom_codes(N, Ns).
drop_digits([D|Cs], Ns) :- code_type(D, digit), !, drop_digits(Cs, Ns).
drop_digits(Ns, Ns).
ecl_temp(X) :- memberchk(X, [value0, env0, cl_env_copy]), !.
ecl_temp(X) :- atom(X), sub_atom(X, 0, _, _, ecl_mv), !.             % ECL's value registers values[k]
ecl_temp(X) :- atom(X), atom_codes(X, [0'd, 0'i, 0'm|Ds]), Ds \== [], forall(member(D, Ds), code_type(D, digit)), !.  % dim0: array index
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
event(S, call(ecl_rplacd, As)) :- call_at(S, ecl_rplacd, As0), !, ecl_term(As0, As).   % `(rplacd);` is `other`
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
    \+ ( sub_term(C, V), compound(C), C = call('$self', _) ),
    \+ V = list(_), \+ V = cons(_, _).          % a new cons is a mutable cell, not a value

% ----- 2. symbolic execution of basic blocks --------------------------------------------------
% st(Env, Elems, Pending): values of variables in the block (in block-entry terms), element
% writes of the block, and the block's writes not yet emitted.
subst(F, Env, Elems, T0, T) :- subst_(F, Env, Elems, T0, T).
subst_(_, _, _, T, T) :- \+ compound(T), !.
subst_(F, Env, _, var(X), T) :- !,
    ( get_assoc(X, Env, V) -> T = V
    ; T = var(X), ( F \== none, ecl_temp(X), \+ ecl_lispvar(F, X) -> assertz(ecl_unresolved(F, X)) ; true ) ).
subst_(F, Env, Elems, elem(Q0, I0), T) :- !, subst_(F, Env, Elems, Q0, Q), subst_(F, Env, Elems, I0, I),
    ( member(E-V, Elems), E == elem(Q, I) -> T = V ; ecl_top(elem(Q, I), T) ).
% a term composed from values of the block is normalised again (car of a list just built)
subst_(F, Env, Elems, T0, T) :- T0 =.. [Fn|As], maplist(subst_(F, Env, Elems), As, Bs), T1 =.. [Fn|Bs], ecl_top(T1, T).

% symex(F, Evs, Stable, Items): items it(S, Line, What) in source order;
% What = label(N) | goto(N, C, P) | st(Kind, Facts)
symex(F, Evs, Stable, Items) :- symex(Evs, F, Stable, st(Stable, [], []), Items).
symex([], F, _, St, Items) :- flush(F, St, _, Items, []).
symex([ev(S, L, E)|Evs], F, Stable, St0, Items) :- step(E, S, L, F, Stable, St0, St, Items, Rest),
    symex(Evs, F, Stable, St, Rest).

step(write(var(X), V0), S, L, F, _, st(Env0, El, P), st(Env, El, P1), Items, Items) :- !,
    subst(F, Env0, El, V0, V),
    ( lisp_var(F, X), ( V = list(_) ; V = cons(_, _) ) -> Read = cur(var(X)) ; Read = V ),   % a new cell: its identity
    put_assoc(X, Env0, Read, Env),
    ( lisp_var(F, X), V \== var(X) -> append(P, [w(S, L, var(X), V)], P1) ; P1 = P ).   % x = x: nothing
step(write(elem(Q0, I0), V0), S, L, F, _, st(Env, El0, P), st(Env, [elem(Q, I)-V|El1], P1), Items, Items) :- !,
    subst(F, Env, El0, Q0, Q), subst(F, Env, El0, I0, I), subst(F, Env, El0, V0, V),
    exclude(same_key(elem(Q, I)), El0, El1), append(P, [w(S, L, elem(Q, I), V)], P1).
step(label(N), S, L, F, Stable, St, st(Stable, [], []), Items, Rest) :- !,
    flush(F, St, _, Items, [it(S, L, label(N))|Rest]).
step(goto(N, C0, P), S, L, F, Stable, St, st(Stable, [], []), Items, Rest) :- !,
    flush(F, St, Env, Items, [it(S, L, goto(N, C, P))|Rest]), ( C0 == none -> C = none ; subst(F, Env, [], C0, C) ).
step(ret(V0), S, L, F, Stable, St, st(Stable, [], []), Items, Rest) :- !,
    flush(F, St, Env, Items, [it(S, L, st(ret, [ret(S, V)]))|Rest]), subst(F, Env, [], V0, V).
% rplacd(cell, list(x)): its operands are read BEFORE the block's writes are emitted (the cell is
% the list's old last cons, kept in a temporary); the list gains x at its end
step(call(Fn, [A0, B0]), S, L, F, _, st(Env0, El, P), st(Env, [], []), Items, Rest) :-
    memberchk(Fn, [ecl_rplacd, 'ECL_RPLACD', cl_rplacd]), !,
    subst(F, Env0, El, A0, A1), subst(F, Env0, El, B0, B1), uncur(A1, A),
    ( B1 = cur(T), member(w(_, _, T2, VB), P), T2 == T -> B = VB ; uncur(B1, B) ),   % the cell just made
    ( B = list([X]) -> Fact = call_at(S, collect, [A, X]) ; Fact = call_at(S, rplacd, [A, B]) ),
    Items = [it(S, L, st(call, [Fact]))|Items1],          % it reads the values before the block's writes
    flush(F, st(Env0, El, P), Env, Items1, Rest).
step(call(Fn, As0), S, L, F, _, St, st(Env, [], []), Items, Rest) :-
    flush(F, St, Env, Items, [it(S, L, st(call, [call_at(S, Fn, As)]))|Rest]), subst(F, Env, [], As0, As).
same_key(K, E-_) :- E == K.

% flush: emit the pending writes; afterwards variables hold their new values, so the block's
% environment keeps only temporaries whose values do not read a replaced target
flush(_, st(Env, _, []), Env, Items, Items) :- !.
flush(_, st(Env0, _, P0), Env, Items, Rest) :-
    last_writes(P0, P),
    findall(T, ( member(w(_, _, T0, _), P), uncur(T0, T) ), Ts),
    (   parallel(P)
    ->  P = [w(S1, L1, _, _)|_], findall(V, ( member(w(_, _, _, V0), P), uncur(V0, V) ), Vs),
        Items = [it(S1, L1, st(assign, [par_assign(S1, Ts, Vs)]))|Rest]
    ;   findall(it(S, L, st(assign, [assign(S, T, V)])), ( member(w(S, L, T, V0), P), uncur(V0, V) ), Ws),
        append(Ws, Rest, Items)
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
parallel(P) :- nth1(K, P, w(_, _, _, V)), nth1(J, P, w(_, _, T, _)), J < K, old_read(V, T), !.

% ----- 2b. def-use webs of escaping temporaries ------------------------------------------------
% ECL reuses one temporary (value0, v8) for unrelated values: the value of an (or ...) and later the
% result. Reaching definitions over the item CFG (successors: the next item unless the item is a
% jump or a return, and the jump target) give, for every use, the definitions that reach it; the
% definitions reaching a common use form one web (Chaitin), and each web is its own variable.
split_webs(F, Items0, Items) :-
    findall(X, ecl_lispvar(F, X), Xs0), sort(Xs0, Xs),
    item_succs(Items0, Succ), foldl(split_web(Succ), Xs, Items0, Items).

item_succs(Items, Succ) :-
    length(Items, Len),
    findall(I-Ss, ( nth1(I, Items, it(_, _, W)), findall(J, item_succ(Items, Len, I, W, J), Ss) ), Succ).
item_succ(Items, _, _, goto(N, _, _), J) :- label_pos(Items, N, J).
item_succ(_, Len, I, W, J) :- \+ W = goto(_, none, none), \+ W = st(ret, _), J is I + 1, J =< Len.

split_web(Succ, X, Items0, Items) :-
    findall(I, ( nth1(I, Items0, It), item_defines(It, X) ), Defs),
    (   Defs = [_, _|_]
    ->  length(Items0, Len), Bound is Len + 1,
        reaching(Succ, Items0, X, Bound, In),
        findall(R, ( nth1(I, Items0, It), item_uses(It, X), memberchk(I-R, In), R \== [] ), Rs),
        findall([D], member(D, Defs), Singles), foldl(merge_web, Rs, Singles, Webs),
        (   Webs = [_, _|_]
        ->  findall(It, ( nth1(I, Items0, It0), rename_item(X, Webs, In, I, It0, It) ), Items)
        ;   Items = Items0 )
    ;   Items = Items0
    ).
% IN[i] = union of OUT[p] over predecessors; OUT[i] = {i} where i defines X, else IN[i];
% iterated at most Bound times (sets only grow; a path of the CFG has at most Len items)
reaching(Succ, Items, X, Bound, In) :-
    findall(I-[], member(I-_, Succ), In0), reaching_(Succ, Items, X, Bound, In0, In).
reaching_(_, _, _, 0, In, In) :- !.
reaching_(Succ, Items, X, B, In0, In) :-
    findall(J-Out, ( member(I-Ss, Succ), member(J, Ss), memberchk(I-InI, In0), nth1(I, Items, It),
                     ( item_defines(It, X) -> Out = [I] ; Out = InI ) ), Edges),
    findall(J-R, ( member(J-_, In0), findall(D, ( member(J2-O, Edges), J2 == J, member(D, O) ), Ds), sort(Ds, R) ), In1),
    ( In1 == In0 -> In = In0 ; B1 is B - 1, reaching_(Succ, Items, X, B1, In1, In) ).
merge_web(R, Webs0, [Merged|Rest]) :-
    partition([W]>>( member(D, W), memberchk(D, R) ), Webs0, Hit, Rest),
    append(Hit, Merged0), sort(Merged0, Merged).
web_name(X, Webs, Ds, N) :- nth1(K, Webs, W), member(D, Ds), memberchk(D, W), !, atomic_list_concat([X, '_w', K], N).

item_defines(it(_, _, st(_, Fs)), X) :- ( member(assign(_, var(X2), _), Fs), X2 == X
                                        ; member(par_assign(_, Ts, _), Fs), memberchk(var(X), Ts) ), !.
item_uses(it(_, _, goto(_, C, _)), X) :- C \== none, sub_term(V, C), V == var(X), !.
item_uses(it(_, _, st(_, Fs)), X) :- member(Fa, Fs), fact_reads(Fa, R), sub_term(V, R), V == var(X), !.
fact_reads(assign(_, T, V), R) :- ( T = var(_) -> R = V ; R = T-V ).
fact_reads(par_assign(_, Ts, Vs), Ts1-Vs) :- exclude([T]>>(T = var(_)), Ts, Ts1).
fact_reads(ret(_, V), V).
fact_reads(call_at(_, _, As), As).

% uses read the web reaching the item, the definition (if any) writes the item's own web
rename_item(X, Webs, In, I, it(S, L, W0), it(S, L, W)) :-
    memberchk(I-R, In), ( web_name(X, Webs, R, Nu) -> true ; Nu = X ),
    ( web_name(X, Webs, [I], Nd) -> true ; Nd = X ),
    rename_what(X, Nu, Nd, W0, W).
rename_what(X, Nu, _, goto(N, C0, P), goto(N, C, P)) :- !, replace_term(var(X), var(Nu), C0, C).
rename_what(X, Nu, Nd, st(K, Fs0), st(K, Fs)) :- !, maplist(rename_fact(X, Nu, Nd), Fs0, Fs).
rename_what(_, _, _, W, W).
rename_fact(X, Nu, Nd, assign(S, T0, V0), assign(S, T, V)) :- !, replace_term(var(X), var(Nu), V0, V),
    ( T0 == var(X) -> T = var(Nd) ; replace_term(var(X), var(Nu), T0, T) ).
rename_fact(X, Nu, Nd, par_assign(S, Ts0, Vs0), par_assign(S, Ts, Vs)) :- !,
    maplist(replace_term(var(X), var(Nu)), Vs0, Vs),
    maplist([T0, T]>>( T0 == var(X) -> T = var(Nd) ; replace_term(var(X), var(Nu), T0, T) ), Ts0, Ts).
rename_fact(X, Nu, _, F0, F) :- replace_term(var(X), var(Nu), F0, F).

% ----- 2b'. copy propagation of single-definition temporaries across blocks ---------------------
% A compiler temporary (ECL drops Lisp names ending in a digit: i1 is v5) with ONE definition
% t := v replaces its later uses when no item between the definition and the use writes an
% operand of v (kill check); a use before the definition (next iteration) keeps t.
copy_temps(F, Items0, Items) :-
    findall(X, ( ecl_lispvar(F, X0), ( X = X0 ; atom(X0), member(it(_, _, st(_, Fs)), Items0),
                 member(assign(_, var(X), _), Fs), atom_concat(X0, '_w', P), sub_atom(X, 0, _, _, P) ) ), Xs0),
    sort(Xs0, Xs), foldl(copy_temp, Xs, Items0, Items).
copy_temp(X, Items0, Items) :-
    findall(D-V, ( nth1(D, Items0, It), It = it(_, _, st(_, Fs)), member(assign(_, var(X2), V), Fs), X2 == X ), Defs),
    (   Defs = [D-V], V \= var(_), pure_value(V),     % no call: nothing allocated, nothing done twice
        \+ ( sub_term(var(Y), V), Y == X )
    ->  findall(Y, ( sub_term(var(Y), V), atom(Y) ), Ops),
        findall(It, ( nth1(U, Items0, It0), copy_use(Items0, X, D, V, Ops, U, It0, It) ), Items)
    ;   Items = Items0
    ).
pure_value(V) :- atomic(V), !.
pure_value(call(F, As)) :- memberchk(F, [len, ecl_array_dimension]), !, forall(member(A, As), pure_value(A)).   % reads only
pure_value(V) :- V =.. [F|As], memberchk(F, [op, elem, tail, var, int, bool]), !,
    forall(member(A, As), ( is_list(A) -> forall(member(B, A), pure_value(B)) ; pure_value(A) )).
copy_use(Items, X, D, V, Ops, U, it(S, L, W0), it(S, L, W)) :-
    U > D, \+ ( between(D, U, K), K > D, K < U, nth1(K, Items, It), member(Y, Ops), item_defines(It, Y) ), !,
    rename_what_use(X, V, W0, W).
copy_use(_, _, _, _, _, _, It, It).
rename_what_use(X, V, goto(N, C0, P), goto(N, C, P)) :- !, replace_term(var(X), V, C0, C).
rename_what_use(X, V, st(K, Fs0), st(K, Fs)) :- !, maplist(copy_fact(X, V), Fs0, Fs).
rename_what_use(_, _, W, W).
copy_fact(X, V, assign(S, T0, V0), assign(S, T, V1)) :- !, replace_term(var(X), V, V0, V1),
    ( T0 == var(X) -> T = T0 ; replace_term(var(X), V, T0, T) ).
copy_fact(X, V, F0, F) :- replace_term(var(X), V, F0, F).

% ----- 2c. function objects: what the tree says, nothing assumed --------------------------------
% (funcall f a b) with f's value known (#'* through a temporary) is that function (operator table);
% a parameter p called with two arguments whose result is used ONLY as a branch or loop test is a
% comparator: an order test op(lt, [a, b]) (the families never depend on its direction); any
% other call of a function object stays an unknown call.
% an &key parameter whose default is #'identity (ecl_key_default, from the tree) applied to x is x
known_calls(Items0, Items) :-
    findall(K, member(it(_, _, st(call, [call_at(_, ecl_key_default, [var(K), call(ecl_symbol, [var(identity)])])])), Items0), Ids),
    exclude([it(_, _, st(call, [call_at(_, ecl_key_default, _)]))]>>true, Items0, Items1),
    maplist(known_item(Ids), Items1, Items).
known_item(Ids, it(S, L, W0), it(S, L, W)) :- known_term(Ids, W0, W).
known_term(_, T, T) :- \+ compound(T), !.
known_term(Ids, T0, T) :- T0 =.. [Fn|As], maplist(known_term(Ids), As, Bs), T1 =.. [Fn|Bs],
    (   T1 = call(ecl_funcall, [fn(Op), A, B]) -> T = op(Op, [A, B])
    ;   T1 = call(ecl_funcall, [var(K), X]), memberchk(K, Ids) -> T = X
    ;   T = T1 ).

comparator_calls(F, Items0, Items) :-
    findall(P, ( scope_param(F, P), comparator_param(Items0, P) ), Ps0), sort(Ps0, Ps),
    foldl(comparator_param_calls, Ps, Items0, Items).
% a parameter of F, or one F's closure captured from its enclosing function (the cell v0<name>)
scope_param(F, P) :- param(F, _, P0), ecl_term(var(P0), var(P)).
scope_param(F, P) :- func(F, N, _), atom_codes(N, [0'L, 0'C|_]), param(G, _, P0), G \== F, ecl_term(var(P0), var(P)).
comparator_param(Items, P) :-
    once(( member(it(_, _, goto(_, C, _)), Items), funcall_of(C, P, _) )),
    \+ ( member(it(_, _, st(_, Fs)), Items), funcall_of(Fs, P, _) ).
funcall_of(T, P, Call) :- sub_term(Call, T), compound(Call), Call = call(ecl_funcall, [V0, _, _]),
    ( V0 = call(cl_complement, [V]) -> true ; V = V0 ), V == var(P).
comparator_param_calls(P, Items0, Items) :- maplist(comparator_item(P), Items0, Items).
comparator_item(P, it(S, L, goto(N, C0, Pol)), it(S, L, goto(N, C, Pol))) :- !, comparator_term(P, C0, C).
comparator_item(_, It, It).
comparator_term(P, T0, T) :- compound(T0), T0 = call(ecl_funcall, [V, A, B]), V == var(P), !,
    comparator_term(P, A, A1), comparator_term(P, B, B1), T = op(lt, [A1, B1]).
comparator_term(P, T0, T) :- compound(T0), T0 = call(ecl_funcall, [call(cl_complement, [V]), A, B]), V == var(P), !,
    comparator_term(P, A, A1), comparator_term(P, B, B1), T = op(not, [op(lt, [A1, B1])]).   % (complement p)
comparator_term(_, T, T) :- \+ compound(T), !.
comparator_term(P, T0, T) :- T0 =.. [Fn|As], maplist(comparator_term(P), As, Bs), T =.. [Fn|Bs].

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
% a conditional goto that only skips exits of its loop is the loop's test (a guarded RETURN inside
% the loop is not: it is a test of the body, e.g. the divisor test of (loop ... never (zerop (rem n i))))
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
    ;   T1 is T - 1, nth1(T1, Items, it(_, _, st(ret, _))),          % then-part returns: after the
        \+ ( goto_at(Items, I2, N, _, _, _), I2 \== I, nth1(I, Items, it(_, _, goto(N, _, _))) ),   % only jump to T
        ( innermost(Loops, I, lp(_, G3)) -> End3 is G3 + 1 ; length(Items, Len), End3 is Len + 1 ),
        T < K, K < End3, Pol = P
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

% the counter the loop condition tests, stepped by a loop invariant (a basic induction variable:
% x = x + c, c a constant or a variable the loop never writes, as in a sieve's stride)
loop_counter(Facts, Cont, X) :-
    sub_term(V, Cont), compound(V), V = var(X), member(assign(_, var(X2), op(O, [var(X3), Step])), Facts),
    X2 == X, X3 == X, memberchk(O, [add, sub]), invariant_step(Facts, Step), !.
invariant_step(_, int(_)) :- !.
invariant_step(Facts, var(C)) :- \+ ( member(assign(_, var(C2), _), Facts), C2 == C ),
    \+ ( member(par_assign(_, Ts, _), Facts), member(T, Ts), T == var(C) ).

% ----- assembling the new facts of one function ---------------------------------------------
ecl_function(F) :-
    retractall(ecl_unresolved(F, _)), events(F, Evs),
    stable_env(F, Evs, Stable0), symex(F, Evs, Stable0, _),
    forall(ecl_unresolved(F, X), ( ecl_lispvar(F, X) -> true ; assertz(ecl_lispvar(F, X)) )),
    stable_env(F, Evs, Stable), symex(F, Evs, Stable, Items0), split_webs(F, Items0, Items1),
    copy_temps(F, Items1, Items1b), known_calls(Items1b, Items2), comparator_calls(F, Items2, Items),
    loops(Items, Loops),
    findall(Fact, item_fact(F, Items, Loops, Fact), Facts0),
    recursion_facts(F, Facts0, Facts1), list_loops(Facts1, Facts2), collect_loops(Facts2, Facts3),
    fold_fusion(Facts3, Facts4), push_collections(Facts4, Facts),
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
    ;   nth1(B, Items, it(_, _, label(0))), Fact = tail_loop(S)      % TTL: a tail self-call made a loop
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

% ----- 6. list traversal: dolist / loop for x in l / mapcar ------------------------------------
% A cursor c of loop L: c := q before L, c := cdr(c) in L (alone or in a parallel assignment).
% The loops and their cursors are a finite set computed first; each loop is rewritten once.
%   one cursor:  the for-each loop of every language (AP13 lowerers: loop_var x, loop_iter q)
%   k cursors:   lockstep traversal; after j steps cursor i is nthcdr(j, q_i), so car(c_i) is
%                elem(q_i, j): the index loop `for j: ... q_1[j] ... q_2[j]` (zip keeps no positions)
list_loops(Facts0, Facts) :-
    findall(L, member(loop(L, _, cond), Facts0), Ls0), sort(Ls0, Ls),
    foldl(list_loop, Ls, Facts0, Facts).
list_loop(L, Facts0, Facts) :-
    findall(cur(C, Q, S0, Sc), cursor(Facts0, L, C, Q, S0, Sc), Cs0), sort(Cs0, Cs),
    (   Cs == []
    ->  Facts = Facts0
    ;   member(loop(L2, F, cond), Facts0), L2 == L, !,
        foldl(drop_cursor(L), Cs, Facts0, Facts1),
        exclude(list_cursor_fact(L, []), Facts1, Facts2),
        (   Cs = [cur(C, Q, _, _)]
        ->  ( item_of(Facts2, L, C, Sx, X) -> exclude(list_cursor_fact(none, [Sx]), Facts2, Facts3) ; X = C, Facts3 = Facts2 ),
            maplist(replace_term(elem(var(C), int(0)), var(X)), Facts3, Facts4),
            append(Facts4, [loop(L, F, count), loop_var(L, X), loop_iter(L, Q)], Facts)
        ;   atomic_list_concat([position_, L], K),
            foldl(lockstep_cursor(L, K), Cs, Facts2, Facts3),
            append(Facts3, [loop(L, F, count), loop_var(L, K)], Facts)
        )
    ).
cursor(Facts, L, C, Q, S0, Sc) :-
    member(in_loop(Sc, L0), Facts), L0 == L, cursor_step(Facts, Sc, C), atom(C),
    member(assign(S0, var(C2), Q), Facts), C2 == C, S0 \== Sc, \+ ( member(in_loop(S0, L1), Facts), L1 == L ).
cursor_step(Facts, Sc, C) :- member(assign(Sc, var(C), T), Facts), T == tail(var(C), 1).
cursor_step(Facts, Sc, C) :- member(par_assign(Sc, Ts, Vs), Facts), nth1(K, Ts, var(C)), nth1(K, Vs, V), V == tail(var(C), 1).
% x := car(c) in L: the loop's element variable for c
item_of(Facts, L, C, Sx, X) :- member(in_loop(Sx, L0), Facts), L0 == L, member(assign(Sx, var(X), E), Facts),
    E == elem(var(C), int(0)), !.
% the cursor's statements go: its initialisation and its step (a parallel assignment keeps the rest)
drop_cursor(_, cur(C, _, S0, Sc), Facts0, Facts) :-
    exclude(list_cursor_fact(none, [S0]), Facts0, Facts1),
    (   member(par_assign(Sc, Ts, Vs), Facts1), memberchk(var(C), Ts)
    ->  findall(T-V, ( nth1(I, Ts, T), nth1(I, Vs, V), T \== var(C) ), Rest),
        ( Rest = [T1-V1] -> New = assign(Sc, T1, V1)
        ; pairs_keys_values(Rest, Ts1, Vs1), New = par_assign(Sc, Ts1, Vs1) ),
        maplist(replace_fact(par_assign(Sc, Ts, Vs), New), Facts1, Facts)
    ;   exclude(list_cursor_fact(none, [Sc]), Facts1, Facts)
    ).
lockstep_cursor(L, K, cur(C, Q, _, _), Facts0, Facts) :-
    E = elem(Q, var(K)),
    (   item_of(Facts0, L, C, Sx, X)
    ->  exclude(list_cursor_fact(none, [Sx]), Facts0, Facts1), maplist(replace_term(var(X), E), Facts1, Facts2)
    ;   Facts2 = Facts0
    ),
    maplist(replace_term(elem(var(C), int(0)), E), Facts2, Facts).
list_cursor_fact(L, _, loop(L2, _, cond)) :- L2 == L.
list_cursor_fact(L, _, loop_cond(L2, _)) :- L2 == L.
list_cursor_fact(L, _, loop_var(L2, _)) :- L2 == L.
list_cursor_fact(_, Drop, Fact) :- fact_about(Fact, S), memberchk(S, Drop).
fact_about(Fact, S) :- Fact =.. [P, S0|_], memberchk(P, [stmt, assign, par_assign, guard, in_loop, next_stmt, ret, call_at]), S = S0.
fact_about(next_stmt(_, S), S).
replace_term(Old, New, T0, T) :- T0 == Old, !, T = New.
replace_term(_, _, T, T) :- \+ compound(T), !.
replace_term(Old, New, T0, T) :- T0 =.. [F|As], maplist(replace_term(Old, New), As, Bs), T =.. [F|Bs].

% ----- 7. loop ... collect: h := list(nil); c := h; in L: c := list(x), rplacd(old c, ...) ---------
% the list h (its cdr is the result) receives x in loop L: the neutral append(h, x)
collect_loops(Facts0, Facts) :-
    (   member(call_at(Sr, collect, [var(C), X]), Facts0), member(in_loop(Sr, L), Facts0),
        member(assign(S0, var(C2), var(H)), Facts0), C2 == C, \+ member(in_loop(S0, L), Facts0),
        member(assign(Sh, var(H2), list([bool(false)])), Facts0), H2 == H
    ->  findall(S1, ( member(assign(S1, var(C3), _), Facts0), C3 == C ), Cs),
        exclude(list_cursor_fact(none, Cs), Facts0, Facts1),
        maplist(replace_term(tail(var(H), 1), var(H)), Facts1, Facts2),
        maplist(replace_fact(assign(Sh, var(H), list([bool(false)])), assign(Sh, var(H), list([]))), Facts2, Facts3),
        maplist(replace_fact(call_at(Sr, collect, [var(C), X]), call_at(Sr, append, [var(H), X])), Facts3, Facts4),
        collect_loops(Facts4, Facts)
    ;   Facts = Facts0
    ).
replace_fact(Old, New, F0, F) :- ( F0 == Old -> F = New ; F = F0 ).

% ----- 7b. push + reverse: r := cons(x, r) for a local r that is returned as (reverse r) ----------
% the standard Lisp accumulation idiom; the output collection receives x (AP13's append)
push_collections(Facts0, Facts) :-
    findall(R, ( member(ret(_, call(reverse, [var(R)])), Facts0), atom(R),
                 \+ ( member(assign(_, var(R2), V), Facts0), R2 == R, \+ pushed_or_empty(V, R) ) ), Rs0),
    sort(Rs0, Rs), foldl(push_collection, Rs, Facts0, Facts).
pushed_or_empty(cons(_, var(R2)), R) :- R2 == R.
pushed_or_empty(bool(false), _).
pushed_or_empty(list([]), _).
push_collection(R, Facts0, Facts) :-
    maplist(push_fact(R), Facts0, Facts1), maplist(replace_term(call(reverse, [var(R)]), var(R)), Facts1, Facts).
push_fact(R, assign(S, var(R2), cons(X, var(R3))), call_at(S, append, [var(R), X])) :- R2 == R, R3 == R, !.
push_fact(R, assign(S, var(R2), bool(false)), assign(S, var(R), list([]))) :- R2 == R, !.
push_fact(_, F, F).

% ----- 8. fold fusion (deforestation): reduce(op, h) of a list h built in loop L is the loop
% with the accumulator h := h op x, started at op's identity -----------------------------------
fold_fusion(Facts0, Facts) :-
    (   member(Fa, Facts0), sub_term(R, Fa), compound(R), R = call(Fold, [int(_), fn(Op), A]), fold(Fold),
        fold_identity(Op, Id), folded_list(Facts0, A, H),
        member(call_at(Sa, append, [V, X]), Facts0), V == var(H),
        member(assign(Sh, var(H2), list([])), Facts0), H2 == H
    ->  maplist(replace_term(R, var(H)), Facts0, Facts1),
        maplist(replace_fact(call_at(Sa, append, [var(H), X]), assign(Sa, var(H), op(Op, [var(H), X]))), Facts1, Facts2),
        maplist(replace_fact(assign(Sh, var(H), list([])), assign(Sh, var(H), Id)), Facts2, Facts3),
        fold_fusion(Facts3, Facts)
    ;   Facts = Facts0
    ).
% (reduce #'op l) and (apply #'op l) = (op x1 x2 ...): the same fold
fold(cl_reduce).
fold(cl_apply).
fold_identity(mul, int(1)).
fold_identity(add, int(0)).
folded_list(_, var(H), H).
folded_list(Facts, var(T), H) :- member(assign(_, var(T2), var(H)), Facts), T2 == T.

% the old facts of F go; the lowerer's recursion loop statement stays
retract_function(F) :-
    findall(S, ( stmt(S, F, K, _), \+ ( K == loop, loop(S, F, recursion) ) ), Ss),
    forall(member(S, Ss), ( retractall(stmt(S, _, _, _)), retractall(guard(S, _, _)), retractall(assign(S, _, _)),
                            retractall(par_assign(S, _, _)), retractall(ret(S, _)), retractall(call_at(S, _, _)),
                            retractall(in_loop(S, _)), retractall(next_stmt(S, _)), retractall(next_stmt(_, S)),
                            retractall(loop(S, _, _)), retractall(loop_var(S, _)), retractall(loop_cond(S, _)),
                            retractall(loop_iter(S, _)), retractall(tail_loop(S)) )),
    forall(loop(LR, F, recursion), ( retractall(in_loop(_, LR)), retractall(loop_cond(LR, _)) )).

% compiled function L<k><name> is the Lisp function <name>; parameters lose ECL's v<k> prefix
% (a top-level form, compiled as ecl_toplevel by ecl_compile.py, is <toplevel> as in the AP13 lowerers)
rename_function(F) :-
    func(F, N0, Line), compiled_name(N0, N1), !, ( N1 == ecl_toplevel -> N = '<toplevel>' ; N = N1 ),
    retract(func(F, N0, Line)), assertz(func(F, N, Line)),
    forall(retract(param(F, K, P0)), ( ecl_term(var(P0), var(P)), assertz(param(F, K, P)) )).
rename_function(_).

ecl_normalise :- forall(func(F, _, _), ecl_function(F)), forall(func(F, _, _), rename_function(F)),
    inline_helpers.

% ----- 9. inlining of one-expression helpers ---------------------------------------------------
% A function of the file whose whole body is one returned expression without calls of itself
% (hlt(i) = hrt(i) - 1, hrt(i) = (i + 1) * 2) is replaced at its calls by that expression with the
% arguments substituted (bounded rounds: helpers of helpers); an inlined affine index in one
% variable is written a*x + b (2*i + 1), the form the AP13 heap idiom reads.
inline_helpers :-
    findall(Name-Ps-Body, inlinable(Name, Ps, Body), Hs),
    (   Hs == [] -> true
    ;   forall(member(P/A, [assign/3, par_assign/3, ret/2, call_at/3, guard/3, loop_cond/2]),
               ( functor(H, P, A), forall(retract(H), ( inline_term(Hs, 3, H, H1), assertz(H1) )) ))
    ).
inlinable(Name, Ps, Body) :-
    func(G, Name, _), atom(Name), Name \== '<toplevel>',
    findall(S, ( stmt(S, G, K, _), K \== loop ), [S]), ret(S, Body),
    \+ ( sub_term(C, Body), compound(C), C = call('$self', _) ),
    findall(K-P, param(G, K, P), KPs), msort(KPs, Sorted), pairs_values(Sorted, Ps).
% depth-bounded (3): a helper's body is itself inlined, so helpers of helpers resolve, and calls
% that would go deeper (mutually calling helpers) stay calls
inline_term(_, _, T, T) :- \+ compound(T), !.
inline_term(Hs, D, call(Name, Args0), T) :- D > 0, member(Name-Ps-Body, Hs), length(Ps, L), length(Args0, L), !,
    maplist(inline_term(Hs, D), Args0, Args), D1 is D - 1, inline_term(Hs, D1, Body, Body1),
    foldl([P, A, B0, B]>>replace_term(var(P), A, B0, B), Ps, Args, Body1, T0), affine(T0, T).
inline_term(Hs, D, T0, T) :- T0 =.. [F|As], maplist(inline_term(Hs, D), As, Bs), T =.. [F|Bs].
affine(T0, T) :- lin(T0, X, A, B), nonvar(X), A > 1, !,
    ( B =:= 0 -> T = op(mul, [int(A), var(X)]) ; B > 0 -> T = op(add, [op(mul, [int(A), var(X)]), int(B)])
    ; NB is -B, T = op(sub, [op(mul, [int(A), var(X)]), int(NB)]) ).
affine(T, T).
lin(var(X), X, 1, 0) :- atom(X).
lin(int(N), _, 0, N) :- integer(N).
lin(op(add, [P, Q]), X, A, B) :- lin(P, X, A1, B1), lin(Q, X, A2, B2), A is A1 + A2, B is B1 + B2.
lin(op(sub, [P, Q]), X, A, B) :- lin(P, X, A1, B1), lin(Q, X, A2, B2), A is A1 - A2, B is B1 - B2.
lin(op(mul, [P, int(K)]), X, A, B) :- integer(K), lin(P, X, A1, B1), A is A1 * K, B is B1 * K.
lin(op(mul, [int(K), P]), X, A, B) :- integer(K), lin(P, X, A1, B1), A is A1 * K, B is B1 * K.

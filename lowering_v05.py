"""Behaviour-lowering rules of the closing round (doc 04 section 19.17), each a language's own semantics the v0.4
lowering missed; installed by crosslang_frontends.install on AP13's behaviour lowerer (to_prolog.PNFLowerer).
  Tried and dropped (19.17): a C declarator without a value (int i;) as nothing, not a read: the code it lets run
          names fibonacci-sequence-2.c climbing_stairs and sorting-algorithms-pancake-sort-2.c reverse_array (a lone
          reversal helper), both true behaviour, wrong labels
  C       an expression with an effect is effect(Statement, Value) (prolog/interp_v04.pl): --n is n = n - 1 then n;
          n++ is t = n, n = n + 1 then t; a = e is the assignment then a; a, b is a then b (a comma statement: a; b)
  C       arrays as C sizes them, counted in elements: int a[3] = {1, 2} is [1, 2, 0]; int c[4]; four zero cells;
          int b[] = {4, 5} its list; a[N][M] rows of fresh cells; malloc(n) and calloc(n, s) n and n*s cells;
          sizeof of an array its length, of anything else 1 (sizeof a / sizeof a[0] is the length); free() nothing
  C       a cast to an integer type truncates (int()), to float or double is float(), to a pointer the same value;
          strlen of a string is its length (a C string is the list of its characters); number literals as C reads
          them (0x1F, 017, 10L, 2.0f)
  Python  (from pnf_v03.PNFv03, kept out of the pipeline until now) a lambda is the value lambda(Params, Body).
          Tried and dropped: a generator as a call's only argument as one comprehension (pnf_v03 has it): the code
          it lets run reads characters as numbers (int('7') is 55: happy_number), 19.17
  Lisp    (case k (1 a) ((2 3) b) (t c)) compares k with eql against each key, t or otherwise the default (ecase too);
          (subseq s a b) is the slice s[a:b], (setf (subseq s a b) v) stores into it; &optional parameters: the function of the required ones
          gives the defaults and calls name$full, which takes all of them, as does a call that passes more
  Lisp    (last l) is the list of its last element, the slice l[-1:]; (map 'list f s) is (mapcar f s); both only
          where the program defines no function of that name
"""
import compare_learners
compare_learners._ap13()

_installed = False


def declarator_name(d):
    """(name, [array sizes, outermost first], is_pointer) of a C declarator."""
    sizes, pointer = [], False
    while d is not None and d.type != 'identifier':
        if d.type == 'array_declarator':
            sizes.append(d.child_by_field_name('size'))
        elif d.type == 'pointer_declarator':
            pointer = True
        elif d.type not in ('parenthesized_declarator',):
            return None, sizes, pointer
        d = d.child_by_field_name('declarator') or (d.named_children[0] if d.named_children else None)
    return (d.text.decode() if d is not None else None), sizes[::-1], pointer   # m[2][3]: tree-sitter nests the last size outermost


def install_lisp():
    import lisp_to_prolog as lp
    cls, Sym = lp.LispPNF, lp.Sym
    defun0, run0, place0 = cls.defun, cls.run, cls.place

    def f_case(self, a):
        sk, k = self.compile(a[0])
        key = self.fresh()
        t = self.fresh()
        tree = ('skip',)
        for clause in reversed(a[1:]):
            keys = clause[0]
            sb, vb = self.compile_body(clause[1:])
            if isinstance(keys, Sym) and str(keys) in ('t', 'otherwise'):
                c = ('bool', 'true')
            else:
                tests = []
                for x in (keys if isinstance(keys, list) else [keys]):
                    _, xv = self.compile([Sym('quote'), x]) if isinstance(x, Sym) else self.compile(x)
                    tests.append(('op', 'eq', [('var', key), xv]))
                c = tests[0] if tests else ('bool', 'false')
                for x in tests[1:]:
                    c = ('op', 'or', [c, x])
            tree = ('if', c, ('seq', sb + [('assign', ('var', t), vb)]), tree)
        return sk + [('assign', ('var', key), k), ('assign', ('var', t), ('bool', 'false')), tree], ('var', t)

    def place(self, p):
        if isinstance(p, list) and p and p[0] == 'subseq' and len(p) in (3, 4):
            s1, q = self.compile(p[1])
            s2, a = self.compile(p[2])
            s3, b = self.compile(p[3]) if len(p) == 4 else ([], ('none',))
            return s1 + s2 + s3, ('slice', q, a, b, ('none',))
        return place0(self, p)

    def defun(self, f):
        lam = f[2] if len(f) > 2 and isinstance(f[2], list) else []
        if '&optional' not in lam or any(x in lam for x in ('&key', '&rest', '&body')):
            return defun0(self, f)
        i = lam.index('&optional')
        req = [str(x) for x in lam[:i]]
        opt, aux = [], []
        mode = 'opt'
        for x in lam[i + 1:]:
            if x == '&aux':
                mode = 'aux'
                continue
            (opt if mode == 'opt' else aux).append(x)
        names = [str(x[0] if isinstance(x, list) else x) for x in opt]
        defaults = [x[1] if isinstance(x, list) and len(x) > 1 else Sym('nil') for x in opt]
        name = str(f[1])
        full = [Sym('defun'), Sym(name + '$full'), [Sym(n) for n in req + names] + ([Sym('&aux')] + aux if aux else [])] + list(f[3:])
        defun0(self, full)
        pre = []
        for n, d in zip(names, defaults):
            sd, vd = self.compile(d)
            pre += sd + [('assign', ('var', n), vd)]
        self.funs.append((name, req, ('seq', pre + [('return', ('call', name + '$full', [('var', n) for n in req + names]))])))
        self.optional = getattr(self, 'optional', {})
        self.optional[name] = (len(req), defaults)

    def run(self, src):
        self.own_names = {str(f[1]) for f in lp.read_all(src)
                          if isinstance(f, list) and len(f) > 1 and f[0] == 'defun'}
        funs = run0(self, src)
        opt = getattr(self, 'optional', {})
        if not opt:
            return funs

        def fix(t):
            if isinstance(t, tuple) and t[:1] == ('call',) and len(t) == 3 and t[1] in opt and len(t[2]) > opt[t[1]][0]:
                req, defaults = opt[t[1]]
                args = [fix(a) for a in t[2]]
                pad = []
                for d in defaults[len(args) - req:]:
                    sd, vd = self.compile(d)
                    if sd:
                        return t
                    pad.append(vd)
                return ('call', t[1] + '$full', args + pad)
            if isinstance(t, tuple):
                return tuple(fix(x) if i else x for i, x in enumerate(t))
            if isinstance(t, list):
                return [fix(x) for x in t]
            return t
        out = [(n, ps, fix(b)) for n, ps, b in funs]
        import io_trace                       # the wrapper's sequence parameters are the full function's (as
        bodies = {n: b for n, _, b in out}    # haskell_core_pnf marks a list parameter with len(p))
        for k, (n, ps, b) in enumerate(out):
            if n in opt and n + '$full' in bodies:
                listy = [p for p in ps if io_trace._uses(bodies[n + '$full'], p) == 'list']
                if listy:
                    out[k] = (n, ps, ('seq', [('expr', ('call', 'len', [('var', p)])) for p in listy] + [b]))
        self.funs[:] = out
        return self.funs

    def f_subseq(self, a):
        s1, q = self.compile(a[0])
        s2, i = self.compile(a[1])
        s3, j = self.compile(a[2]) if len(a) > 2 else ([], ('none',))
        return s1 + s2 + s3, ('slice', q, i, j, ('none',))

    def f_last(self, a):
        if len(a) != 1 or 'last' in getattr(self, 'own_names', ()):
            return self.compile_call('last', a)
        s1, q = self.compile(a[0])
        return s1, ('slice', q, ('int', -1), ('none',), ('none',))

    def f_map(self, a):
        if len(a) == 3 and 'map' not in getattr(self, 'own_names', ()):
            return self.f_mapcar(a[1:])
        return self.compile_call('map', a)

    cls.f_case = cls.f_ecase = f_case
    cls.f_last, cls.f_map = f_last, f_map
    cls.f_subseq = f_subseq
    def compile_call(self, h, args):          # a call of the program's own function (no special form)
        sa, vs = self.many(args)
        return sa, ('call', lp.BUILTIN.get(h, h), vs)
    cls.compile_call = compile_call
    cls.place, cls.defun, cls.run = place, defun, run


def install():
    global _installed
    if _installed:
        return
    _installed = True
    install_lisp()
    import to_prolog
    cls = to_prolog.PNFLowerer
    st0, expr0, fun0 = cls.st, cls.expr, cls.function

    def function(self, node, roles, prefix, name=None):
        if self.lang == 'c':
            self.c_arrays, stack = set(), [node]
            while stack:
                n = stack.pop()
                if n.type == 'array_declarator' or (n.type == 'parameter_declaration' and b'[' in n.text):
                    nm = declarator_name(n if n.type == 'array_declarator' else n.child_by_field_name('declarator'))[0]
                    if nm:
                        self.c_arrays.add(nm)
                stack.extend(n.named_children)
        return fun0(self, node, roles, prefix, name)

    def st(self, node, implicit=False):
        if self.lang == 'c' and node is not None and node.parent is not None and node.parent.type == 'declaration' \
                and node.type in ('init_declarator', 'array_declarator'):
            decl = node.child_by_field_name('declarator') if node.type == 'init_declarator' else node
            name, sizes, pointer = declarator_name(decl)
            value = node.child_by_field_name('value') if node.type == 'init_declarator' else None
            if name is not None and sizes:
                ns = ('list', [self.expr(z) if z is not None else ('none',) for z in sizes])
                init = self.expr(value) if value is not None else ('list', [])
                return ('assign', ('var', name), ('call', 'c_array', [init, ns]))
            if name is not None and pointer and value is not None:
                return ('assign', ('var', name), self.expr(value))
        if self.lang == 'c' and node is not None and node.type == 'expression_statement' and node.named_children \
                and node.named_children[0].type == 'call_expression' \
                and node.named_children[0].child_by_field_name('function').text == b'free':
            return ('skip',)
        if self.lang == 'c' and node is not None and node.type == 'comma_expression':
            return ('seq', [self.st(c) for c in node.named_children])
        return st0(self, node, implicit)

    def expr(self, node):
        if self.lang == 'python' and node is not None:
            if node.type == 'lambda' and (node.start_byte, node.end_byte) not in getattr(self, 'rf_bodies', {}):
                ps = node.child_by_field_name('parameters')     # (a returned lambda is returns_function's, 19.8)
                names = [c.child_by_field_name('name') or c for c in ps.named_children] if ps is not None else []
                if all(n.type == 'identifier' for n in names):
                    return ('lambda', [n.text.decode() for n in names], self.expr(node.child_by_field_name('body')))
        if self.lang == 'c' and node is not None:
            if node.type == 'update_expression' and node.named_children:
                t = expr0(self, node.named_children[0])
                step = ('assign', t, ('op', 'sub' if '--' in node.text.decode() else 'add', [t, ('int', 1)]))
                if node.children[0].type in ('++', '--'):            # prefix: the new value
                    return ('effect', step, t)
                self.effect_tmp = getattr(self, 'effect_tmp', 0) + 1
                tmp = ('var', f'post${self.effect_tmp}')
                return ('effect', ('seq', [('assign', tmp, t), step]), tmp)
            if node.type == 'number_literal':
                t = node.text.decode().replace("'", '')
                if not t.lower().startswith('0x'):
                    t = t.rstrip('uUlLfF') if any(c in t for c in '.eE') else t.rstrip('uUlL')
                else:
                    t = t.rstrip('uUlL')
                try:
                    return ('int', int(t, 0)) if not t.lower().startswith('0x') and not any(c in t for c in '.eE') \
                        and not (len(t) > 1 and t.startswith('0')) else ('int', int(t, 16)) if t.lower().startswith('0x') \
                        else ('int', int(t, 8)) if not any(c in t for c in '.eE') else ('num', float(t))
                except ValueError:
                    return expr0(self, node)
            if node.type == 'initializer_list':
                return ('list', [self.expr(c) for c in node.named_children])
            if node.type == 'sizeof_expression':
                v = node.child_by_field_name('value')
                while v is not None and v.type == 'parenthesized_expression' and v.named_children:
                    v = v.named_children[0]
                return ('call', 'len', [('var', v.text.decode())]) if v is not None and v.type == 'identifier' \
                    and getattr(self, 'c_arrays', None) is not None and v.text.decode() in self.c_arrays else ('int', 1)
            if node.type == 'call_expression' and node.child_by_field_name('function') is not None \
                    and node.child_by_field_name('function').text in (b'malloc', b'calloc'):
                args = [self.expr(a) for a in node.child_by_field_name('arguments').named_children]
                n = args[0] if len(args) == 1 else ('op', 'mul', args[:2])
                return ('call', 'c_array', [('list', []), ('list', [n])])
            if node.type == 'cast_expression' and node.child_by_field_name('value') is not None:
                v, ty = self.expr(node.child_by_field_name('value')), node.child_by_field_name('type')
                tt = ty.text.decode() if ty is not None else ''
                if '*' in tt:                                    # a pointer cast: the same cells
                    return v
                if any(w in tt.split() for w in ('float', 'double')):
                    return ('call', 'float', [v])
                return ('call', 'int', [v])                      # an integer type truncates
            if node.type == 'call_expression' and node.child_by_field_name('function') is not None \
                    and node.child_by_field_name('function').text == b'strlen':
                return ('call', 'len', [self.expr(a) for a in node.child_by_field_name('arguments').named_children])
            if node.type == 'comma_expression' and len(node.named_children) == 2:
                return ('effect', self.st(node.named_children[0]), self.expr(node.named_children[1]))
            if node.type == 'assignment_expression' and node.child_by_field_name('left') is not None:
                return ('effect', self.st(node), expr0(self, node.child_by_field_name('left')))
        return expr0(self, node)

    cls.st, cls.expr, cls.function = st, expr, function

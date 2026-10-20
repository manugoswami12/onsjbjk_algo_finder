"""A function that returns a function (doc 04 section 19.8), lowered as a new function.
A Python function RETURNS A FUNCTION when every return of its own body gives a lambda (with the same parameters).
It is then lowered exactly as a new function is, recursively: f(x) returning lambda y: E is the function f(x, y)
whose returns give E (E a lambda again: repeat); the statements before the return stay (they make the closure).
A chained call h(a)(b) of such a function of the file is h(a, b). Otherwise nothing changes (a function returning a
value). install(): the structure lowerer (imperative_logic, the tree) and the behaviour lowerer (to_prolog, the
battery); called by crosslang_frontends.install."""
import compare_learners
compare_learners._ap13()

NESTED = ('function_definition', 'lambda', 'class_definition')


def own_returns(fnode):
    """The return statements of fnode's own body (not of the functions or lambdas inside it)."""
    out, stack = [], list(fnode.child_by_field_name('body').named_children)
    while stack:
        n = stack.pop()
        if n.type in NESTED:
            continue
        if n.type == 'return_statement':
            out.append(n)
        stack.extend(n.named_children)
    return out


def lambda_params(lam):
    p = lam.child_by_field_name('parameters')
    return [c.text.decode() for c in (p.named_children if p is not None else []) if c.type == 'identifier']


def unwrap(lam):
    """lambda a: lambda b: E -> ([a, b], E)."""
    params = []
    while lam is not None and lam.type == 'lambda':
        params += lambda_params(lam)
        lam = lam.child_by_field_name('body')
    return params, lam


def returned_function(fnode):
    """(extra parameters, {returned lambda: its body}) when every own return gives a lambda with the same
    parameters, else None (the function returns a value)."""
    if fnode.child_by_field_name('body') is None:
        return None
    rets = own_returns(fnode)
    vals = [r.named_children[0] if r.named_children else None for r in rets]
    if not vals or any(v is None or v.type != 'lambda' for v in vals):
        return None
    shapes = [unwrap(v) for v in vals]
    if any(s[0] != shapes[0][0] for s in shapes):
        return None
    return shapes[0][0], {(v.start_byte, v.end_byte): body for v, (_, body) in zip(vals, shapes)}


def function_returning_names(root):
    names, stack = set(), [root]
    while stack:
        n = stack.pop()
        if n.type == 'function_definition' and returned_function(n) is not None:
            names.add(n.child_by_field_name('name').text.decode())
        stack.extend(n.named_children)
    return names


def chain(node):
    """h(a)(b)(c) -> (h, [a-args, b-args, c-args]) when the innermost callee is a name, else None."""
    argss = []
    while node is not None and node.type == 'call':
        argss.insert(0, node.child_by_field_name('arguments'))
        node = node.child_by_field_name('function')
    return (node.text.decode(), argss) if node is not None and node.type == 'identifier' and len(argss) > 1 else None


_installed = False


def install(facts=True, pnf=True):
    global _installed
    if _installed:
        return
    _installed = True
    import imperative_logic
    import to_prolog
    classes = ([imperative_logic.ImperativeLowerer] if facts else []) + ([to_prolog.PNFLowerer] if pnf else [])
    for cls in classes:
        run0, fun0, par0, expr0 = cls.run, cls.function, cls.params, cls.expr

        def run(self, root, run0=run0):
            self.rf_names = function_returning_names(root) if self.lang == 'python' else set()
            self.rf_bodies, self.rf_extra = {}, {}
            return run0(self, root)

        def function(self, node, roles, prefix, name=None, fun0=fun0):
            rf = returned_function(node) if self.lang == 'python' else None
            if rf is not None:
                extra, bodies = rf
                self.rf_extra[(node.start_byte, node.end_byte)] = extra
                self.rf_bodies.update(bodies)
            return fun0(self, node, roles, prefix, name)

        def params(self, node, roles, par0=par0):
            return par0(self, node, roles) + getattr(self, 'rf_extra', {}).get((node.start_byte, node.end_byte), [])

        def expr(self, node, expr0=expr0):
            if node is not None and getattr(self, 'rf_bodies', None):
                body = self.rf_bodies.get((node.start_byte, node.end_byte))
                if body is not None and node.type == 'lambda':
                    return self.expr(body)                      # the returned function's value
            if node is not None and node.type == 'call' and getattr(self, 'rf_names', None):
                c = chain(node)
                if c is not None and c[0] in self.rf_names:
                    return self.call_term(c[0], [a for args in c[1] for a in self.args(args)])
            return expr0(self, node)
        cls.run, cls.function, cls.params, cls.expr = run, function, params, expr

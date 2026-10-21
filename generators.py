"""A Python generator, lowered for behaviour as the list it yields (doc 04 section 19.14).
A function whose own body has `yield e` statements (and no `yield from`, no yield inside an expression) gives the
values it yields, in order: it is lowered as acc = [] at the start, each `yield e` as acc.append(e), each return and
the end of the body as return acc. Otherwise nothing changes. install(): the behaviour lowerer (to_prolog)."""
import compare_learners
compare_learners._ap13()

NESTED = ('function_definition', 'lambda', 'class_definition')
ACC = 'yield$acc'


def own_yields(fnode):
    """The yield nodes of fnode's own body, or None when one is not a plain `yield e` statement."""
    body = fnode.child_by_field_name('body')
    out, stack = [], list(body.named_children) if body is not None else []
    while stack:
        n = stack.pop()
        if n.type in NESTED:
            continue
        if n.type == 'yield':
            plain = n.parent is not None and n.parent.type in ('expression_statement', 'block') and len(n.named_children) == 1 \
                and not any(c.type == 'from' for c in n.children)
            if not plain:
                return None
            out.append(n)
        stack.extend(n.named_children)
    return out


_installed = False


def install():
    global _installed
    if _installed:
        return
    _installed = True
    import to_prolog
    cls = to_prolog.PNFLowerer
    fun0, st0 = cls.function, cls.st

    def function(self, node, roles, prefix, name=None):
        ys = own_yields(node) if self.lang == 'python' and node.type == 'function_definition' else None
        if not ys:
            return fun0(self, node, roles, prefix, name)
        outer, self.gen_yields = getattr(self, 'gen_yields', None), {(y.start_byte, y.end_byte) for y in ys}
        try:
            n = fun0(self, node, roles, prefix, name)
        finally:
            self.gen_yields = outer
        i = next(k for k in range(len(self.funs) - 1, -1, -1) if self.funs[k][0] == n)
        fname, ps, body = self.funs[i]
        self.funs[i] = (fname, ps, ('seq', [('assign', ('var', ACC), ('list', [])), body, ('return', ('var', ACC))]))
        return n

    def st(self, node, implicit=False):
        gy = getattr(self, 'gen_yields', None)
        if gy and node is not None:
            if node.type == 'yield' and (node.start_byte, node.end_byte) in gy:
                return ('expr', ('call', 'append', [('var', ACC), self.expr(node.named_children[0])]))
            if node.type == 'return_statement':
                return ('return', ('var', ACC))
        return st0(self, node, implicit)

    cls.function, cls.st = function, st

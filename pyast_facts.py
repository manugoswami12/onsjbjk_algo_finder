"""Facts Python tells about its own programs (doc 04 section 19.7), added to the tree-sitter facts of a Python file:
which names hold lists, and which functions return lists. Python's own ast reads the source (static: the program is
never run); tree-sitter stays the parser, and a file Python's ast cannot parse gets no extra facts.

  list_var(Function, Name)   every assignment of Name in Function gives a list, or Name is appended to / extended
  list_func(Function)        every return of Function gives a list (a recursive call included: a fixed point)
  list_param(Function, Name) the parameter Name is sliced in Function (a slice of it is a list)

A list: a list literal or comprehension, list(...) or sorted(...), a slice of a list or of a sliced parameter, a `+`
with a list operand, a list name, or a call of a function of the file that returns a list. Function names are
qualified as the lowerers name them (outer.inner, Class.method). prolog/ast_concat.pl uses the facts to read `+` on
lists as concat.
"""
from __future__ import annotations

import ast
from pathlib import Path

LIST_CALLS = {'list', 'sorted'}


def _functions(tree):
    """{qualified name: FunctionDef}, nested functions as outer.inner and methods as Class.method."""
    out = {}

    def walk(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[prefix + child.name] = child
                walk(child, prefix + child.name + '.')
            elif isinstance(child, ast.ClassDef):
                walk(child, prefix + child.name + '.')
            else:
                walk(child, prefix)
    walk(tree, '')
    return out


def _own(f):
    """The nodes of f, not of the functions nested in it."""
    stack = list(ast.iter_child_nodes(f))
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield n
        stack.extend(ast.iter_child_nodes(n))


class _Lists:
    def __init__(self, tree):
        self.funcs = _functions(tree)
        self.short = {}
        for q in self.funcs:
            self.short.setdefault(q.split('.')[-1], set()).add(q)
        self.list_funcs: set[str] = set()
        self.names: dict[str, set[str]] = {q: set() for q in self.funcs}
        for _ in range(6):                                  # names and functions together, to a fixed point
            changed = False
            for q, f in self.funcs.items():
                names = self._names(q, f)
                if names != self.names[q]:
                    self.names[q], changed = names, True
            new = {q for q, f in self.funcs.items() if self._returns_list(q, f)}
            if new != self.list_funcs:
                self.list_funcs, changed = new, True
            if not changed:
                break

    def sliced_params(self, f):
        params = {a.arg for a in f.args.args}
        return {n.value.id for n in _own(f) if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Slice)
                and isinstance(n.value, ast.Name) and n.value.id in params}

    def _names(self, q, f):
        assigned, appended = {}, set()
        for n in _own(f):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        assigned.setdefault(t.id, []).append(n.value)
            elif isinstance(n, ast.AnnAssign) and n.value is not None and isinstance(n.target, ast.Name):
                assigned.setdefault(n.target.id, []).append(n.value)          # x: list[int] = ...
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ('append', 'extend') \
                    and isinstance(n.func.value, ast.Name):
                appended.add(n.func.value.id)
        names = set(appended)
        for _ in range(6):
            grow = {v for v, vals in assigned.items() if all(self.is_list(e, q, f, names) for e in vals)}
            if grow <= names:
                break
            names |= grow
        return names

    def _returns_list(self, q, f):
        rets = [n.value for n in _own(f) if isinstance(n, ast.Return) and n.value is not None]
        return bool(rets) and all(self.is_list(r, q, f, self.names[q]) for r in rets)

    def is_list(self, e, q, f, names):
        if isinstance(e, (ast.List, ast.ListComp)):
            return True
        if isinstance(e, ast.Name):
            return e.id in names
        if isinstance(e, ast.Subscript) and isinstance(e.slice, ast.Slice):
            return self.is_list(e.value, q, f, names) or (isinstance(e.value, ast.Name)
                                                          and e.value.id in {a.arg for a in f.args.args})
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Add):
            return self.is_list(e.left, q, f, names) or self.is_list(e.right, q, f, names)
        if isinstance(e, ast.IfExp):
            return self.is_list(e.body, q, f, names) and self.is_list(e.orelse, q, f, names)
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Name):
            return e.func.id in LIST_CALLS or any(c in self.list_funcs for c in self.short.get(e.func.id, ()))
        return False


def _atom(s: str) -> str:
    return "'" + s.replace('\\', '\\\\').replace("'", "\\'") + "'"


def facts(path: Path) -> str:
    """The list facts of a Python file, as Prolog text ('' when Python's ast cannot parse it)."""
    try:
        tree = ast.parse(path.read_text(encoding='utf-8', errors='replace'))
    except (SyntaxError, ValueError, RecursionError):
        return ''
    info = _Lists(tree)
    out = [f'list_var({_atom(q)},{_atom(n)}).' for q in info.funcs for n in sorted(info.names[q])]   # each
    out += [f'list_param({_atom(q)},{_atom(n)}).' for q, f in info.funcs.items() for n in sorted(info.sliced_params(f))]
    out += [f'list_func({_atom(q)}).' for q in sorted(info.list_funcs)]                       # predicate together
    return ('\n'.join(out) + '\n') if out else ''

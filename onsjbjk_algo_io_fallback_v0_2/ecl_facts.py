"""Facts for one ECL-compiled Lisp function: the AP13 language-neutral facts of its C.

ECL's C uses labels and goto for every loop; the AP13 C lowerer does not descend into labelled
statements. With tree-sitter (the parser the lowerer itself uses) each label becomes the marker
statement `ecl_label(N);` and each goto `ecl_goto(N);`, so the unchanged lowerer emits them as
ordinary call statements with lines and guards; prolog/ecl_norm.pl turns them into loops.
Calls through the symbol table, `ecl_function_dispatch(env, VV[k])(n, args) /* NAME */`, become
`name(args)` (ECL's own C name mangling) and calls of a function object (funcall of a parameter)
`ecl_funcall(f, args)`. Only the compiled Lisp functions (`L<n><name>`) are kept, not ECL's module
initialiser (local functions LC<k>name are kept); each ECL unit is parsed on its own (the initialiser's `#ifdef extern "C"` is not C).
"""
from __future__ import annotations

import bisect
import re
import tempfile
from pathlib import Path

import compare_learners

compare_learners._ap13()
import cli
import tree_sitter_language_pack as pack

PARSER = pack.get_parser('c')


def label_number(name: str) -> str:
    return name.lstrip('LT') or '0'           # TTL (tail-call top) -> 0, L12 -> 12


def c_name(lisp_name: str) -> str:
    return ''.join(ch if ch.isalnum() else '_' for ch in lisp_name.lower())


def line_comments(root, src: bytes) -> dict:
    """{line: [(byte offset, text)]} of every comment, in one top-down pass. Only byte offsets are
    read: in tree-sitter 0.26 node.parent / next_sibling / start_point corrupted memory here."""
    starts = [0] + [i + 1 for i, ch in enumerate(src) if ch == 0x0A]
    rows: dict = {'starts': starts}
    stack = [root]
    while stack:
        n = stack.pop()
        if n.type == 'comment':
            rows.setdefault(bisect.bisect_right(starts, n.start_byte), []).append(
                (n.start_byte, src[n.start_byte:n.end_byte].decode('utf-8', 'replace').strip('/* ')))
        stack.extend(n.children)
    return rows


def trailing_comment(node, comments: dict):
    """ECL's /* NAME */ after a call or cell on the same line."""
    end = node.end_byte
    after = sorted(c for c in comments.get(bisect.bisect_right(comments['starts'], end - 1), []) if c[0] >= end)
    return after[0][1] if after else None


def callee(node, inner_target, src: bytes, comments: dict):
    """Lisp name of a dispatched call: ECL_SYM("NAME",n), else ECL's trailing /* NAME */ comment."""
    if inner_target.type == 'call_expression':
        fn = inner_target.child_by_field_name('function')
        if src[fn.start_byte:fn.end_byte] == b'ECL_SYM':
            first = inner_target.child_by_field_name('arguments').named_children[0]
            return c_name(src[first.start_byte:first.end_byte].decode().strip('"'))
    name = trailing_comment(node, comments)
    return c_name(name) if name else None


def scoped_names(fn) -> dict:
    """ECL re-declares temporaries (`cl_object v8;`) in nested blocks: every later declaration of a
    name in a function is a different variable, renamed v8_1, v8_2 for its scope (C block scoping)."""
    renames, count = {}, {}

    def walk(node, scopes):
        if node.type == 'compound_statement':
            scopes = [*scopes, {}]
        elif node.type == 'declaration':
            for d in node.children_by_field_name('declarator'):
                while d.type != 'identifier' and d.child_by_field_name('declarator') is not None:
                    d = d.child_by_field_name('declarator')
                if d.type == 'identifier':
                    name = d.text.decode()
                    k = count[name] = count.get(name, -1) + 1
                    scopes[-1][name] = f'{name}_{k}' if k else name
        elif node.type == 'identifier':
            name = node.text.decode()
            new = next((sc[name] for sc in reversed(scopes) if name in sc), name)
            if new != name:
                renames[(node.start_byte, node.end_byte)] = new
            return
        for child in node.children:
            walk(child, scopes)
    walk(fn, [{}])
    return renames


def closure_cells(root, src: bytes, comments: dict) -> dict:
    """ECL keeps a variable captured by a closure in a cell, `lex0[0] = v1list; /* LIST */`, shared
    with the local functions (LC<k>name) of the unit: each cell is that Lisp variable (v0list)."""
    cells = {}
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == 'assignment_expression':
            left = node.child_by_field_name('left')
            text = src[left.start_byte:left.end_byte].decode().replace(' ', '')
            name = trailing_comment(node, comments) if left.type == 'subscript_expression' and text.startswith('lex') else None
            if name:
                cells.setdefault(text, f'v0{c_name(name)}')
        stack.extend(node.children)
    return cells


def lisp_aliases(fn, src: bytes) -> dict:
    """Two Lisp variables of one name (a parameter n and `loop for n ...`: ECL's v1n, v4n) stay two
    variables: each later one is renamed v4n_1. Closure cells (v0<name>) alias on purpose."""
    first, out = {}, {}

    def walk(node):
        if node.type == 'identifier':
            ident = src[node.start_byte:node.end_byte].decode()
            m = re.fullmatch(r'v([1-9]\d*)([A-Za-z]\w*)', ident)
            if m:
                if m.group(2) not in first:
                    first[m.group(2)] = ident
                elif first[m.group(2)] != ident and ident not in out:
                    out[ident] = f'{ident}_{len(out) + 1}'
        for child in node.children:
            walk(child)
    walk(fn)
    return out


def optional_parameters(fn, src: bytes) -> list[str] | None:
    """&optional parameters of a variadic ECL function (`cl_narg narg, ..., ...`), in order: the
    variables set from va_arg; None for an ordinary function."""
    params = fn.child_by_field_name('declarator').child_by_field_name('parameters')
    text = src[params.start_byte:params.end_byte].decode()
    if 'cl_narg' not in text or '...' not in text:
        return None
    names, stack = [], [fn]
    while stack:
        node = stack.pop()
        if node.type == 'assignment_expression':
            right = node.child_by_field_name('right')
            if src[right.start_byte:right.end_byte].decode().startswith('va_arg('):
                left = node.child_by_field_name('left')
                names.append((node.start_byte, src[left.start_byte:left.end_byte].decode()))
        stack.extend(node.children)
    return [n for _, n in sorted(names)]


# a standard function passed as an object (#'*): its neutral operator name
FUNCTION_OBJECT = {'*': 'mul', '+': 'add', '-': 'sub', '/': 'div', 'MAX': 'max', 'MIN': 'min', '<': 'lt',
                   '>': 'gt', '<=': 'le', '>=': 'ge', '=': 'eq'}


def compiled(name: str) -> bool:
    """ECL's C name of a compiled Lisp function: L<k>name, or LC<k>name for a local function."""
    rest = name[2:] if name.startswith('LC') else name[1:] if name.startswith('L') else ''
    return rest[:1].isdigit()


def declared_names(root, src: bytes) -> set:
    """Every variable a function declares or takes (identifiers of declarations and parameters)."""
    names, stack = set(), [root]
    while stack:
        node = stack.pop()
        if node.type in ('declaration', 'parameter_declaration'):
            for d in node.children_by_field_name('declarator'):
                while d.type != 'identifier' and d.child_by_field_name('declarator') is not None:
                    d = d.child_by_field_name('declarator')
                if d.type == 'identifier':
                    names.add(src[d.start_byte:d.end_byte].decode())
        stack.extend(node.children)
    return names


def unambiguous(c_text: str) -> str:
    """Pass 1. ECL parenthesises every macro argument: `(97)<=(v3c) && (v3c)<=(122)`. C's grammar
    cannot tell `(v3c) && x` from a cast of `&&x` (GNU label address) to a type v3c, and tree-sitter
    reads the cast. A "cast" to a name the function declares as a VARIABLE is the variable, and a
    lone name or number loses its parentheses; pass 2 parses the result."""
    src = c_text.encode('utf-8')
    tree = pack.get_parser('c').parse(src)
    variables = declared_names(tree.root_node, src)

    def raw(node) -> str:
        return src[node.start_byte:node.end_byte].decode('utf-8', 'replace')

    def render(node) -> str:
        if node.type == 'cast_expression':
            typ = node.child_by_field_name('type')
            if typ is not None and raw(typ).strip() in variables:
                return f'{raw(typ).strip()} {render(node.child_by_field_name("value"))}'
        if node.type == 'parenthesized_expression' and node.named_child_count == 1 and \
                node.named_children[0].type in ('identifier', 'number_literal'):
            return raw(node.named_children[0])
        out, pos = [], node.start_byte
        for child in node.children:
            out.append(src[pos:child.start_byte].decode('utf-8', 'replace'))
            out.append(render(child))
            pos = child.end_byte
        out.append(src[pos:node.end_byte].decode('utf-8', 'replace'))
        return ''.join(out)
    return render(tree.root_node)


def marked_c(c_text: str) -> str:
    """The compiled Lisp functions of one ECL C unit, rewritten bottom-up (tree rewriting)."""
    src = unambiguous(c_text).encode('utf-8')
    renames: dict = {}
    tree = pack.get_parser("c").parse(src)   # a fresh parser per unit; the Tree must outlive its nodes
    root = tree.root_node
    comments = line_comments(root, src)
    cells = closure_cells(root, src, comments)

    def raw(node) -> str:                       # source slice (not node.text: kept off the binding)
        return src[node.start_byte:node.end_byte].decode('utf-8', 'replace')

    def text(node) -> str:                      # the node's source with its children rewritten
        out, pos = [], node.start_byte
        for child in node.children:
            out.append(src[pos:child.start_byte].decode('utf-8', 'replace'))
            out.append(render(child))
            pos = child.end_byte
        out.append(src[pos:node.end_byte].decode('utf-8', 'replace'))
        return ''.join(out)

    def render(node) -> str:
        if node.type == 'identifier':
            ident = raw(node)
            return renames.get((node.start_byte, node.end_byte), aliases.get(ident, ident))
        if optional is not None and (node.start_byte, node.end_byte) != body:   # &optional: no va_arg prologue
            if node.type == 'parameter_list':
                kept = [raw(c) for c in node.named_children if c.type == 'parameter_declaration' and 'cl_narg' not in raw(c)]
                return '(' + ', '.join([*kept, *(f'cl_object {n}' for n in optional)]) + ')'
            if node.type == 'compound_statement' and 'va_arg(' in raw(node) and 'va_end' not in raw(node):
                return ''
            if node.type == 'expression_statement' and raw(node).startswith(('va_start', 'va_end')):
                return ''
            if node.type == 'declaration' and (raw(node).startswith('va_list') or any(
                    raw(node).replace(' ', '') == f'cl_object{n};' for n in optional)):
                return ''
        if node.type == 'call_expression' and raw(node.child_by_field_name('function')) in variadic:
            args = node.child_by_field_name('arguments').named_children[1:]     # the argument count goes
            return f'{raw(node.child_by_field_name("function"))}({", ".join(render(a) for a in args)})'
        if node.type == 'subscript_expression' and raw(node).replace(' ', '') in cells:
            return cells[raw(node).replace(' ', '')]
        if node.type == 'labeled_statement':
            label = node.child_by_field_name('label')
            rest = [render(c) for c in node.children if c.start_byte > label.end_byte and c.type != ':']
            return f'ecl_label({label_number(raw(label))});\n' + ' '.join(rest)
        if node.type == 'goto_statement':
            return f'ecl_goto({label_number(raw(node.child_by_field_name("label")))});'
        if node.type == 'field_expression' and raw(node).replace(' ', '').endswith('->symbol.gfdef'):
            sym = node.child_by_field_name('argument')
            sym = sym.child_by_field_name('argument') if sym.type == 'field_expression' else sym
            if sym.type == 'call_expression' and raw(sym.child_by_field_name('function')) == 'ECL_SYM':
                name = raw(sym.child_by_field_name('arguments').named_children[0]).strip('"')
                return f'ecl_function({FUNCTION_OBJECT.get(name, c_name(name))})'
        if node.type == 'comma_expression' and node.child_count >= 3:
            # (ECL_CONS_CDR(t)=x, t): the tail of a cons is set (rplacd), as `loop ... collect` does
            left = node.children[0]
            if left.type == 'assignment_expression':
                target = left.child_by_field_name('left')
                if target.type == 'call_expression' and raw(target.child_by_field_name('function')) == 'ECL_CONS_CDR':
                    cell = render(target.child_by_field_name('arguments').named_children[0])
                    return f'ecl_rplacd({cell}, {render(left.child_by_field_name("right"))})'
            # (ecl_floor2(a,b), cl_env_copy->values[1]): the remainder, second value of floor / truncate
            left, right = node.children[0], node.children[2]
            if (left.type == 'call_expression' and raw(left.child_by_field_name('function')) in ('ecl_floor2', 'ecl_truncate2')
                    and raw(right).replace(' ', '') == 'cl_env_copy->values[1]'):
                return 'ecl_rem' + text(left.child_by_field_name('arguments'))
        if node.type == 'call_expression' and node.child_by_field_name('function').type == 'call_expression':
            inner = node.child_by_field_name('function')
            if raw(inner.child_by_field_name('function')) == 'ecl_function_dispatch':
                target = inner.child_by_field_name('arguments').named_children[-1]
                args = [render(a) for a in node.child_by_field_name('arguments').named_children[1:]]
                name = None if target.type == 'identifier' else callee(node, target, src, comments)
                if name is None:
                    return f'ecl_funcall({", ".join([render(target), *args])})'
                return f'{name}({", ".join(args)})'
        return text(node)

    kept, aliases, optional, body, variadic = [], {}, None, None, set()
    for node in root.children:
        if node.type == 'function_definition':
            decl = node.child_by_field_name('declarator')
            name = decl.child_by_field_name('declarator') if decl is not None else None
            if name is not None and compiled(raw(name)):
                renames, aliases = scoped_names(node), lisp_aliases(node, src)
                optional, fbody = optional_parameters(node, src), node.child_by_field_name('body')
                body = (fbody.start_byte, fbody.end_byte)
                if optional is not None:
                    variadic.add(raw(name))
                kept.append(render(node))
    return '\n\n'.join(kept)


def facts_of(units: list[str]) -> str:
    """AP13 neutral facts (existing lowerer) of the marked C of all units (one function id space)."""
    with tempfile.TemporaryDirectory(prefix='v02_eclf_') as td:
        f = Path(td) / 'unit.c'
        f.write_text('\n\n'.join(marked_c(u) for u in units if u), encoding='utf-8')
        _, facts = cli.facts_text(f)
    return facts

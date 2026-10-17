"""Facts for one ECL-compiled Lisp function: the AP13 language-neutral facts of its C.

ECL's C uses labels and goto for every loop; the AP13 C lowerer does not descend into labelled
statements. With tree-sitter (the parser the lowerer itself uses) each label becomes the marker
statement `ecl_label(N);` and each goto `ecl_goto(N);`, so the unchanged lowerer emits them as
ordinary call statements with lines and guards; prolog/ecl_norm.pl turns them into loops.
Calls through the symbol table, `ecl_function_dispatch(env, VV[k])(n, args) /* NAME */`, become
`name(args)` (ECL's own C name mangling) and calls of a function object (funcall of a parameter)
`ecl_funcall(f, args)`. Only the compiled Lisp functions (`L<n><name>`) are kept, not ECL's module
initialiser; each ECL unit is parsed on its own (the initialiser's `#ifdef extern "C"` is not C).
"""
from __future__ import annotations

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


def callee(node, inner_target):
    """Lisp name of a dispatched call: ECL_SYM("NAME",n), else ECL's trailing /* NAME */ comment."""
    if inner_target.type == 'call_expression' and inner_target.child_by_field_name('function').text == b'ECL_SYM':
        return c_name(inner_target.child_by_field_name('arguments').named_children[0].text.decode().strip('"'))
    n = node
    while n is not None and n.type not in ('expression_statement', 'compound_statement'):
        sib = n.next_sibling
        if sib is not None and sib.type == 'comment' and sib.start_point.row == node.end_point.row:
            return c_name(sib.text.decode().strip('/* '))
        n = n.parent
    return None


def marked_c(c_text: str) -> str:
    """The compiled Lisp functions of one ECL C unit, rewritten bottom-up (tree rewriting)."""
    src = c_text.encode('utf-8')

    def text(node) -> str:                      # the node's source with its children rewritten
        out, pos = [], node.start_byte
        for child in node.children:
            out.append(src[pos:child.start_byte].decode('utf-8', 'replace'))
            out.append(render(child))
            pos = child.end_byte
        out.append(src[pos:node.end_byte].decode('utf-8', 'replace'))
        return ''.join(out)

    def render(node) -> str:
        if node.type == 'labeled_statement':
            label = node.child_by_field_name('label')
            rest = [render(c) for c in node.children if c.start_byte > label.end_byte and c.type != ':']
            return f'ecl_label({label_number(label.text.decode())});\n' + ' '.join(rest)
        if node.type == 'goto_statement':
            return f'ecl_goto({label_number(node.child_by_field_name("label").text.decode())});'
        if node.type == 'comma_expression' and node.child_count >= 3:
            # (ecl_floor2(a,b), cl_env_copy->values[1]): the remainder, ECL's second value of floor
            left, right = node.children[0], node.children[2]
            if (left.type == 'call_expression' and left.child_by_field_name('function').text == b'ecl_floor2'
                    and right.text.replace(b' ', b'') == b'cl_env_copy->values[1]'):
                return 'ecl_rem' + text(left.child_by_field_name('arguments'))
        if node.type == 'call_expression' and node.child_by_field_name('function').type == 'call_expression':
            inner = node.child_by_field_name('function')
            if inner.child_by_field_name('function').text == b'ecl_function_dispatch':
                target = inner.child_by_field_name('arguments').named_children[-1]
                args = [render(a) for a in node.child_by_field_name('arguments').named_children[1:]]
                name = None if target.type == 'identifier' else callee(node, target)
                if name is None:
                    return f'ecl_funcall({", ".join([target.text.decode(), *args])})'
                return f'{name}({", ".join(args)})'
        return text(node)

    kept = []
    for node in PARSER.parse(src).root_node.children:
        if node.type == 'function_definition':
            decl = node.child_by_field_name('declarator')
            name = decl.child_by_field_name('declarator') if decl is not None else None
            if name is not None and name.text.decode().startswith('L') and name.text.decode()[1:2].isdigit():
                kept.append(render(node))
    return '\n\n'.join(kept)


def facts_of(units: list[str]) -> str:
    """AP13 neutral facts (existing lowerer) of the marked C of all units (one function id space)."""
    with tempfile.TemporaryDirectory(prefix='v02_eclf_') as td:
        f = Path(td) / 'unit.c'
        f.write_text('\n\n'.join(marked_c(u) for u in units if u), encoding='utf-8')
        _, facts = cli.facts_text(f)
    return facts

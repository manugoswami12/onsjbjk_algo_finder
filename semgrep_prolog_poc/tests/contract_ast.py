"""AP3 SYNTHETIC structural contract fixture.

Derived from the REAL binary Semgrep dump, augmented with predictive For,
Container(Tuple), and parallel-assignment shapes. This is NOT a real parsed
Semgrep result and never substitutes for the live Windows acceptance test.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / 'tests' / 'fixtures' / 'semgrep_binary_ast.json'


def ident(name):
    return {'N': {'Id': [[name, '()'], {}]}}


def integer(n):
    return {'L': {'Int': [{'some': n}, '()']}}


def op(operator, x, y):
    return {'Call': [
        {'Special': [{'Op': operator}, '()']},
        [{'Arg': x}, {'Arg': y}],
    ]}


def subscript(name, index):
    return {'ArrayAccess': [ident(name), index, '()']}


def index_plus(name):
    return op('Plus', ident(name), integer(1))


def container(a, b):
    return {'Container': [{'Tuple': '()'}, ['()', [a, b], '()']]}


def bubble_loop(*, swap=True, reverse=True, compare=True):
    lhs = container(subscript('a', ident('j')), subscript('a', index_plus('j')))
    rhs = (container(subscript('a', index_plus('j')), subscript('a', ident('j')))
           if reverse else container(subscript('a', ident('j')), subscript('a', index_plus('j'))))
    then = ({'Block': [{'ExprStmt': [{'Assign': [lhs, '()', rhs]}, '()']}]}
            if swap else {'Block': []})
    cond = op('Gt' if compare else 'Lt', subscript('a', ident('j')), subscript('a', index_plus('j')))
    inner = {'For': ['()', {'ForEach': []}, {'Block': [
        {'If': ['()', {'Cond': cond}, then, None]}
    ]}]}
    return {'For': ['()', {'ForEach': []}, {'Block': [inner]}]}


def merged(*, swap=True, reverse=True, compare=True):
    obj = copy.deepcopy(json.loads(CAPTURE.read_text(encoding='utf-8')))
    defs = obj['Pr'][1]['DefStmt']
    defs[0]['name']['EN']['Id'][0][0] = 'find_number'
    body = defs[1]['FuncDef']['fbody']['FBStmt']['Block']
    body.insert(2, bubble_loop(swap=swap, reverse=reverse, compare=compare))
    return obj


def separate():
    obj = copy.deepcopy(json.loads(CAPTURE.read_text(encoding='utf-8')))
    defstmt = obj['Pr'][1]['DefStmt']
    separate_sort = copy.deepcopy(obj['Pr'][1])
    separate_sort['DefStmt'][0]['name']['EN']['Id'][0][0] = 'arrange'
    separate_sort['DefStmt'][1]['FuncDef']['fbody']['FBStmt']['Block'] = [bubble_loop()]
    defstmt[0]['name']['EN']['Id'][0][0] = 'locate_item'
    obj['Pr'].insert(1, separate_sort)
    return obj

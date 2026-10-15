"""AP6 SYNTHETIC contract fixtures, NOT live Semgrep AST output.

Reuse the captured real AP2 DefStmt wrapper via AP5's contract_ast module,
then add Semgrep-style structural nodes. Live tests separately parse actual files.
"""
from __future__ import annotations
import copy
from contract_ast import merged, bubble_loop, ident, integer, op, subscript


def assign(name, expression):
    return {'ExprStmt': [{'Assign': [ident(name), '()', expression]}, '()']}


def return_name(name):
    return {'Return': ['()', {'some': ident(name)}, '()']}


def hash_update(*, accumulator='digest', old_accumulator=None, array='a',
                index='j', multiplier=31, modulus=1000000007):
    if old_accumulator is None:
        old_accumulator = accumulator
    expr = op('Mod', op('Plus',
                        op('Mult', ident(old_accumulator), integer(multiplier)),
                        subscript(array, ident(index))), integer(modulus))
    return assign(accumulator, expr)


def threaded_ast(*, recurrence=True, swap=True, hash_array='a', hash_index='j',
                 old_acc=None, include_return=True, reset=False,
                 hash_modulus=1000000007, hash_multiplier=31):
    ast = merged()
    defstmt = ast['Pr'][1]['DefStmt']
    defstmt[0]['name']['EN']['Id'][0][0] = 'inspect_items'
    outer = bubble_loop(swap=swap)
    inner = outer['For'][2]['Block'][0]
    if recurrence:
        inner['For'][2]['Block'].insert(0, hash_update(
            array=hash_array, index=hash_index, old_accumulator=old_acc,
            multiplier=hash_multiplier, modulus=hash_modulus))
    body = [assign('digest', integer(0)), outer]
    if reset:
        body.append(assign('digest', integer(123)))
    if include_return:
        body.append(return_name('digest'))
    defstmt[1]['FuncDef']['fbody']['FBStmt']['Block'] = body
    return ast


def separate_threads():
    ast = threaded_ast(swap=False)
    hash_definition = ast['Pr'][1]
    bubble_definition = copy.deepcopy(hash_definition)
    bubble_definition['DefStmt'][0]['name']['EN']['Id'][0][0] = 'sort_only'
    bubble_definition['DefStmt'][1]['FuncDef']['fbody']['FBStmt']['Block'] = [bubble_loop()]
    ast['Pr'].insert(1, bubble_definition)
    return ast

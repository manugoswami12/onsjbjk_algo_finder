"""AP8 test-only AST mutations. NOT a parser and NOT a production recognizer.

Starts from captured *real* Semgrep AST (AP7 out/ast.json for the negative
recurrence example), repairs the one deliberately wrong operand for a positive
synthetic control, then mutates known subtrees adversarially. Live Semgrep
parsing is separately tested on Windows.
"""
import copy
import json
from pathlib import Path

CAPTURE = Path(__file__).resolve().parent / 'fixtures' / 'ap8_actual_semgrep_negative_source.json'


def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)


def source_ast():
    return json.loads(CAPTURE.read_text(encoding='utf-8'))


def main_body(tree):
    return tree['Pr'][1]['DefStmt'][1]['FuncDef']['fbody']['FBStmt']['Block']


def outer_loop(tree):
    return next(x for x in main_body(tree) if isinstance(x, dict) and 'For' in x)


def inner_loop(tree):
    return outer_loop(tree)['For'][2]['Block'][0]


def inner_body(tree):
    return inner_loop(tree)['For'][2]['Block']


def valid_ast():
    tree = source_ast()
    # The real capture contains digest = (other*31 + items[j]) % modulus.
    # Repair only the intentionally wrong identifier as a SYNTHETIC control.
    changed = 0
    for node in walk(inner_body(tree)[0]):
        if 'Id' in node and node['Id'][0][0] == 'other':
            node['Id'][0][0] = 'digest'
            changed += 1
    assert changed == 1, f'unexpected negative fixture shape: {changed}'
    return tree


def invalid_bounds():
    t = valid_ast()
    # Standard canonical inner `range(len(items)-i-1)` -> `...-i-2`.
    arg = inner_loop(t)['For'][1]['ForEach'][2]['Call'][1][0]['Arg']
    minus = arg['Call'][1][1]['Arg']
    assert minus['L']['Int'][0]['some'] == 1
    minus['L']['Int'][0]['some'] = 2
    return t


def hidden_hash_update():
    t = valid_ast()
    statements = inner_body(t)
    update = statements.pop(0)
    # AST-like synthetic subtree; production only receives Semgrep output.
    statements.insert(0, {'If': ['()', {'Cond': {'L': {'Bool': [False, '()']}}},
                                 {'Block': [update]}, None]})
    return t


def premature_return():
    t = valid_ast()
    body = main_body(t)
    original_return = copy.deepcopy(body[-1])
    idx = next(i for i, stmt in enumerate(body) if 'For' in stmt)
    body.insert(idx, original_return)
    return t


def interrupted_loop():
    t = valid_ast()
    inner_body(t).insert(0, {'Break': '()'})
    return t


def renamed_and_rebased():
    t = valid_ast()
    replacements = {'inspect_items':'detect', 'digest':'fingerprint',
                    'items':'values', 'i':'pass_no', 'j':'pos'}
    for node in walk(t):
        for tag in ('Id', 'PatId'):
            if tag in node and isinstance(node[tag], list):
                v = node[tag][0]
                if isinstance(v,list) and v[0] in replacements:
                    v[0] = replacements[v[0]]
    # General constants are independent bindings. Change only hash product.
    update = inner_body(t)[0]['ExprStmt'][0]['Assign'][2]
    product = update['Call'][1][0]['Arg']['Call'][1][0]['Arg']
    product['Call'][1][1]['Arg']['L']['Int'][0]['some'] = 41
    return t

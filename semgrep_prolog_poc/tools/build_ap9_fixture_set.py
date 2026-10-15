#!/usr/bin/env python3
"""Deterministic AP9 fixture builder; test data only, NEVER a recognizer."""
import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from audit_contract_ast import valid_ast, invalid_bounds, source_ast

DEST = ROOT/'tests'/'fixtures'/'ap9_cases'


def walk(x):
    if isinstance(x, dict):
        yield x
        for val in x.values(): yield from walk(val)
    elif isinstance(x, list):
        for val in x: yield from walk(val)


def rename(tree, names):
    t = copy.deepcopy(tree)
    for node in walk(t):
        for tag in ('Id', 'PatId'):
            val = node.get(tag)
            if isinstance(val, list) and val and isinstance(val[0], list) and val[0]:
                if val[0][0] in names:
                    val[0][0] = names[val[0][0]]
        if 'Param' in node:
            pname = node['Param'].get('pname')
            if isinstance(pname, dict) and 'some' in pname:
                val = pname['some']
                if isinstance(val, list) and val[0] in names:
                    val[0] = names[val[0]]
    return t


def alter_op(t):
    t = copy.deepcopy(t)
    for node in walk(t):
        if node.get('Op') == 'Plus':
            node['Op'] = 'Minus'
            return t
    raise AssertionError('missing Plus')


def alter_literal(t):
    t = copy.deepcopy(t)
    for node in walk(t):
        if 'Int' in node and isinstance(node['Int'], list):
            val = node['Int'][0]
            if isinstance(val, dict) and val.get('some') == 2:
                val['some'] = 3
                return t
    raise AssertionError('missing literal 2')


def alter_builtin(t):
    t = copy.deepcopy(t)
    for node in walk(t):
        val = node.get('Id')
        if isinstance(val, list) and val[0][0] == 'len':
            val[0][0] = 'other_builtin'
            return t
    raise AssertionError('missing len')


def save(name, tree):
    (DEST/f'{name}.json').write_text(json.dumps(tree, ensure_ascii=False, indent=1)+'\n',encoding='utf8')


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    binary = json.loads((ROOT/'tests/fixtures/semgrep_binary_ast.json').read_text(encoding='utf8'))
    sort_hash = valid_ast()  # synthetic 1-operand correction of genuine Semgrep capture
    cases = [
        ('binary_exact', binary, [('binary_search_ref','locate_item')]),
        ('binary_renamed', rename(binary, {'locate_item':'renamed_search','lower':'first','upper':'last',
                                           'values':'data','target':'needle','pivot':'center'}),
         [('binary_search_ref','renamed_search')]),
        ('binary_bad_operator', alter_op(binary), []),
        ('binary_bad_literal', alter_literal(binary), []),
        ('binary_bad_builtin', alter_builtin(binary), []),
        ('binary_conflated_names', rename(binary, {'lower':'upper'}), []),
        ('sort_hash_reference', sort_hash, [('sort_hash_ref','inspect_items')]),
        ('sort_hash_renamed', rename(sort_hash, {'inspect_items':'blend', 'items':'records',
                                               'digest':'state','i':'passno','j':'position',
                                               'other':'spare'}), [('sort_hash_ref','blend')]),
        ('sort_hash_wrong_bounds', invalid_bounds(), []),
        ('sort_hash_wrong_state', source_ast(), []),
    ]
    for name, tree, _ in cases:
        save(name, tree)
    dataset = {
        'note': 'Captured real binary AST, AP8 derived synthetic positive interleaved AST; labels manually assigned, not inferred.',
        'references': [
            {'label':'binary_search_ref', 'ast_json':'binary_exact.json','function':'locate_item','region':'body'},
            {'label':'sort_hash_ref', 'ast_json':'sort_hash_reference.json','function':'inspect_items','region':'body'},
        ],
        'cases': [{'id':name,'ast_json':name+'.json',
                   'expected':[{'label':label,'function':fn} for label,fn in expected]}
                  for name,_,expected in cases],
    }
    (DEST/'manifest.json').write_text(json.dumps(dataset, indent=2)+'\n',encoding='utf8')
    print('AP9 sample dataset:',len(cases),'cases,2 reference templates')

if __name__=='__main__':
    main()

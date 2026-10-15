"""AP12-only extra static witness: value-driven bounded interval lookup.

Never claims correctness. Does NOT weaken or modify the 11-case standalone POC.
"""
from __future__ import annotations

import ast
from pathlib import Path


def is_name(e,name):
    return isinstance(e,ast.Name) and e.id==name


def midpoint(e,left,right):
    from static_trace import midpoint as base_midpoint
    return base_midpoint(e,left,right)


def compare_to_target(test,array,center,aliases,params):
    """Return expected update on the condition's TRUE arm, or None.

    Requires indexed value of a distinct argument and another input argument.
    """
    if not isinstance(test,ast.Compare) or len(test.ops)!=1 or len(test.comparators)!=1:
        return None
    op=test.ops[0]
    if not isinstance(op,(ast.Lt,ast.LtE,ast.Gt,ast.GtE)):
        return None
    def kind(expr):
        if isinstance(expr,ast.Subscript) and is_name(expr.value,array) and is_name(expr.slice,center):
            return 'value'
        if isinstance(expr,ast.Name) and expr.id in aliases:
            return 'value'
        if isinstance(expr,ast.Name) and expr.id in params and expr.id!=array:
            return 'target'
        return 'other'
    a,b=kind(test.left),kind(test.comparators[0])
    if (a,b)==('value','target'):
        return 'grow' if isinstance(op,(ast.Lt,ast.LtE)) else 'shrink'
    if (a,b)==('target','value'):
        return 'shrink' if isinstance(op,(ast.Lt,ast.LtE)) else 'grow'
    return None


def bound_action(stmt,left,right,center):
    if not isinstance(stmt,ast.Assign) or len(stmt.targets)!=1:
        return None
    dst=stmt.targets[0]
    if not isinstance(dst,ast.Name):
        return None
    e=stmt.value
    if (dst.id==left and isinstance(e,ast.BinOp) and isinstance(e.op,ast.Add)
        and is_name(e.left,center) and isinstance(e.right,ast.Constant)
        and type(e.right.value)==int and e.right.value==1):
        return 'grow'
    if dst.id==right and (is_name(e,center) or (
        isinstance(e,ast.BinOp) and isinstance(e.op,ast.Sub)
        and is_name(e.left,center) and isinstance(e.right,ast.Constant)
        and type(e.right.value)==int and e.right.value==1)):
        return 'shrink'
    return None


def extra_interval_witness(fn):
    from static_trace import statements
    params={a.arg for a in fn.args.posonlyargs+fn.args.args+fn.args.kwonlyargs}
    rows=list(statements(fn.body))
    result=[]
    # Do not interpret nested declarations or exception/with/match control-flow.
    for loop,_,_ in rows:
        if not isinstance(loop,ast.While):continue
        test=loop.test
        if not (isinstance(test,ast.Compare) and len(test.ops)==1
                and isinstance(test.ops[0],(ast.Lt,ast.LtE))
                and len(test.comparators)==1
                and isinstance(test.left,ast.Name)
                and isinstance(test.comparators[0],ast.Name)):
            continue
        left,right=test.left.id,test.comparators[0].id
        if left==right:continue
        enclosed=[(stmt,guards) for stmt,guards,ls in rows if loop in ls]
        centers=[(stmt.targets[0].id,stmt.lineno) for stmt,_ in enclosed
                 if isinstance(stmt,ast.Assign) and len(stmt.targets)==1
                 and isinstance(stmt.targets[0],ast.Name)
                 and midpoint(stmt.value,left,right)]
        for center,line in centers:
            aliases={}
            for stmt,_ in enclosed:
                if (isinstance(stmt,ast.Assign) and len(stmt.targets)==1
                    and isinstance(stmt.targets[0],ast.Name)
                    and isinstance(stmt.value,ast.Subscript)
                    and isinstance(stmt.value.value,ast.Name)
                    and stmt.value.value.id in params and is_name(stmt.value.slice,center)):
                    aliases[stmt.targets[0].id]=(stmt.value.value.id,stmt.lineno)
            arrays={n.value.id for n,_ in enclosed for n in ast.walk(n)
                    if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name)
                    and n.value.id in params and is_name(n.slice,center)}
            if len(arrays)!=1:continue
            array=next(iter(arrays))
            alias_names={a for a,(source,ln) in aliases.items() if source==array}
            conditions={}
            for stmt,_ in enclosed:
                if isinstance(stmt,ast.If):
                    cond=compare_to_target(stmt.test,array,center,alias_names,params)
                    if cond:conditions[id(stmt)]=cond
            if not conditions:continue
            actions=[]
            for stmt,guards in enclosed:
                action=bound_action(stmt,left,right,center)
                if action and guards:
                    # An update must be on a true/false path of an actual indexed
                    # target comparison, not merely another unrelated conditional.
                    for predicate,truth in guards:
                        expected=conditions.get(id(predicate))
                        if expected and (action==(expected if truth else
                                                ('shrink' if expected=='grow' else 'grow'))):
                            actions.append((action,stmt.lineno))
                            break
            if {x[0] for x in actions}!={'grow','shrink'}:continue
            # Check the output explicitly contains the returned interval end, or a
            # result variable that receives this same center in this loop.
            output_names={s.value.id for s,_,_ in rows if isinstance(s,ast.Return)
                          and isinstance(s.value,ast.Name)}
            saved={s.targets[0].id for s,_ in enclosed
                   if isinstance(s,ast.Assign) and len(s.targets)==1
                   and isinstance(s.targets[0],ast.Name) and is_name(s.value,center)}
            if not (output_names & {left,right,center} or output_names & saved):
                continue
            result.append(line)
    return sorted(set(result))


def enrich(analyses, source):
    """One new fact, only when all required structural witnesses hold."""
    parsed=ast.parse(source)
    functions=[n for n in parsed.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    if len(functions)!=len(analyses):
        raise ValueError('top-level Python AST function count disagrees with fallback')
    for fn,analysis in zip(functions,analyses):
        for lineno in extra_interval_witness(fn):
            analysis.add('bounded_indexed_interval_lookup',lineno)
    return analyses

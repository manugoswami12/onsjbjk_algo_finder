"""AP13 display output: parse the Prolog line protocol and print a readable report."""
from __future__ import annotations

from env_run import ToolError

NOTICE = 'NOT A PROOF OF ALGORITHM IDENTITY OR CORRECTNESS'


def parse_scan(lines):
    funcs, leaves = {}, []
    for line in lines:
        parts = line.split('|')
        tag = parts[0]
        if tag == 'FUNC' and len(parts) == 4:
            funcs[parts[1]] = {'name': parts[2], 'line': parts[3], 'routes': [], 'evidence': [],
                               'unsupported': []}
        elif tag == 'ROUTE' and len(parts) == 3 and parts[1] in funcs:
            funcs[parts[1]]['routes'].append(parts[2])
        elif tag == 'OBS' and len(parts) == 4 and parts[1] in funcs:
            funcs[parts[1]]['evidence'].append(f'{parts[2]}@{parts[3]}')
        elif tag == 'UNSUP' and len(parts) == 4 and parts[1] in funcs:
            funcs[parts[1]]['unsupported'].append(f'{parts[2]}@{parts[3]}')
        elif tag == 'LEAF' and parts[1] == 'MATCH' and len(parts) == 7:
            leaves.append({'result': 'MATCH', 'label': parts[2], 'branch': parts[3],
                           'functions': parts[4], 'bindings': parts[5], 'relations': int(parts[6])})
        elif tag == 'LEAF' and parts[1] == 'PARTIAL' and len(parts) == 6:
            leaves.append({'result': 'PARTIAL', 'label': parts[2], 'branch': parts[3],
                           'present': parts[4], 'missing': parts[5]})
        else:
            raise ToolError('malformed Prolog response: ' + line[:200])
    for f in funcs.values():
        if not f['routes']:
            raise ToolError('Prolog omitted the route of ' + f['name'])
    # G9: most specific (most relations) first
    leaves.sort(key=lambda x: (x['result'] != 'MATCH', -x.get('relations', 0), x['label']))
    return {'functions': list(funcs.values()), 'leaves': leaves}


def identifications(result, meta):
    """Ranked matches collapsed by structural group: [(group_key, [labels...]), ...]."""
    out, seen = [], {}
    for m in (x for x in result['leaves'] if x['result'] == 'MATCH'):
        g = meta.get(m['label'], {}).get('grp') or m['label']
        if g in seen:
            out[seen[g]][1].append(m['label'])
        else:
            seen[g] = len(out)
            out.append((g, [m['label']]))
    return out


def show_scan(path, lang, result, references):
    print(f'AP13_SCAN: {path} language={lang} references={references}')
    for f in result['functions']:
        print(f"FUNCTION: {f['name']} (line {f['line']})")
        print('  BRANCHES: ' + ', '.join(sorted(set(f['routes']))))
        if f['evidence']:
            print('  EVIDENCE: ' + ', '.join(sorted(set(f['evidence']))))
        if f['unsupported']:
            print('  LIMITATIONS: ' + ', '.join(f['unsupported']))
    matches = [x for x in result['leaves'] if x['result'] == 'MATCH']
    partial = [x for x in result['leaves'] if x['result'] == 'PARTIAL']
    for i, m in enumerate(matches):
        tag = 'IDENTIFIED' if i == 0 else 'ALSO CONSISTENT'
        print(f"LEAF MATCH: {m['label']} [{m['branch']}] functions={m['functions']} "
              f"names={m['bindings']} relations={m['relations']} ({tag})")
    for p in partial[:3]:
        print(f"LEAF PARTIAL: {p['label']} [{p['branch']}] relations {p['present']}; missing: {p['missing']}")
    for algo in result.get('library', []):
        print(f'LIBRARY: {algo} (a standard-library call or idiom; no algorithm body to trace)')
    if not matches:
        print('LEAF: UNKNOWN (no learned reference matched completely)')
    print(NOTICE)


def show_status(rows):
    if not rows:
        print('AP13_STATUS: no learned references')
    for r in rows:
        print('AP13_STATUS: ' + ' '.join(f'{k}={v}' for k, v in r.items()))


def library_calls(facts: str) -> list[str]:
    """Algorithms used through a standard-library call or idiom (doc 07): 'gcd', 'sort', ...
    A call to a function defined in the same source is never a library call."""
    import re
    from lang_tables import LIBRARY, PRODUCT_CALLS, RANGE_CALLS
    defined = {n.split('.')[-1].split('/')[0] for n in re.findall(r"func\('?[^,]+'?,'?([^',]+)'?,", facts)}
    called = set(re.findall(r"call_at\('?[^,]+'?,'?([^',\[]+)'?,", facts))
    found = sorted(algo for algo, names in LIBRARY.items() if (names & called) - defined)
    # product/prod over a range from 1 (or 2) to n: the factorial idiom
    prod = '|'.join(PRODUCT_CALLS)
    rng = '|'.join(RANGE_CALLS)
    if re.search(rf"'?call'?\('?({prod})'?,\['?call'?\('?({rng})'?,\['?int'?\([12]\)", facts) \
            or re.search(rf"'?call'?\('?({prod})'?,\['?op'?\('?:'?,\['?int'?\([12]\)", facts):
        found = sorted(set(found) | {'factorial'})
    return found

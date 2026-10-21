"""AP13 v3: input->output family branching (doc 08), added beside the working tools.

Nothing in cli.py / report.py / knowledge_store.py is changed: this module calls
their functions and adds the family level on top.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli import facts_text  # noqa: E402
import tempfile  # noqa: E402

from env_run import AP12_ROUTER, PROLOG_DIR, ToolError, swipl  # noqa: E402


FAMILY_MAIN = PROLOG_DIR / 'family_main.pl'


def run_family(goal: str, facts: str) -> list[str]:
    with tempfile.TemporaryDirectory(prefix='ap13_fam_') as td:
        fp = Path(td) / 'facts.pl'
        fp.write_text(facts, encoding='utf-8')
        return swipl(goal, [AP12_ROUTER, FAMILY_MAIN], [str(fp)])


def _parse(lines):
    rows = []
    for line in lines:
        tag, _, name, path_text = line.split('|', 3)
        if tag not in ('FAMILY', 'ANSWER'):
            raise ToolError('unexpected family output: ' + line[:200])
        rows.append((tag, name, path_text.split('>')))
    return rows


def family_rows(path: Path) -> list:
    """[(tag, function, path)] where tag ANSWER marks the file's answer (doc 09: functions
    with a family that no other function with a family calls); FAMILY marks helpers."""
    _, facts = facts_text(path)
    return _parse(run_family('family_main', facts))


def families(path: Path) -> dict:
    """function name -> list of family paths (each a list, broad -> narrow); all functions."""
    out = {}
    for _, name, p in family_rows(path):
        out.setdefault(name, []).append(p)
    return out


def answers(path: Path) -> dict:
    """Only the answer functions of the file (helpers left out)."""
    out = {}
    for tag, name, p in family_rows(path):
        if tag == 'ANSWER':
            out.setdefault(name, []).append(p)
    return out


def dump(path: Path) -> str:
    _, facts = facts_text(path)
    return '\n'.join(run_family('dump_main', facts))


if __name__ == '__main__':
    cmd, target = sys.argv[1], Path(sys.argv[2])
    if cmd == 'dump':
        print(dump(target))
    else:
        for name, paths in answers(target).items():
            for p in paths:
                print(f'FAMILY: {name}: ' + ' > '.join(p))

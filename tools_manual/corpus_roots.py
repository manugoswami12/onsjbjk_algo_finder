"""Separate tool (doc 04 section 18.6): the root functions of every TheAlgorithms file (prolog/call_roots.pl, as
tools_manual/decide_new_or_known.roots) -> benchmark/corpus_roots.json.

usage: PYTHONPATH=. python tools_manual/corpus_roots.py data/TheAlgorithms-Python
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from decide_new_or_known import roots

import crosslang_frontends
import ta_corpus
from ta_corpus import ROOT

crosslang_frontends.install(lisp_sbcl=False)


def one(corpus: Path, rel: str):
    try:
        return rel, sorted(roots(corpus / rel))
    except Exception:                               # noqa: BLE001  (no facts: no roots)
        return rel, []


if __name__ == '__main__':
    corpus = Path(sys.argv[1])
    rels = sorted(ta_corpus.files(corpus))
    with ThreadPoolExecutor(4) as pool:
        out = dict(pool.map(lambda r: one(corpus, r), rels))
    (ROOT / 'benchmark' / 'corpus_roots.json').write_text(json.dumps(out, indent=0, sort_keys=True) + '\n', encoding='utf-8')
    print(len(out), 'files,', sum(1 for v in out.values() if len(v) == 1), 'with exactly one root')

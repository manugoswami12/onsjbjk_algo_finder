"""Score the mixed answers (mixed_answer.py, doc 04 sections 18.6-18.7) exactly as the pipeline's answers are scored:
eval_decision.py and final_report.py run unchanged, with the mixed answers in place of the pipeline's
(benchmark/mixed_heldout.json for ta_heldout.json, benchmark/mixed_corpus.json for ta_answers.json). Nothing the
pipeline wrote is overwritten.

usage: PYTHONPATH=.:tools_manual python mixed_report.py CORPUS
       -> benchmark/mixed_decision.json, .md, benchmark/mixed_final_report.json, benchmark/MIXED_REPORT.md
"""
from __future__ import annotations

import sys

from ta_corpus import ROOT

B = ROOT / 'benchmark'


def main():
    corpus = sys.argv[1]
    sys.argv = [sys.argv[0], str(B / 'held_decided.json'), str(B / 'corpus_decided.json'), 'node']
    import eval_decision
    eval_decision.HELDOUT = B / 'mixed_heldout.json'
    eval_decision.OUT, eval_decision.REPORT = B / 'mixed_decision.json', B / 'mixed_decision.md'
    eval_decision.main()
    import final_report
    final_report.ANSWERS = B / 'mixed_corpus.json'
    final_report.DECISION = eval_decision.OUT
    final_report.OUT, final_report.REPORT = B / 'mixed_final_report.json', B / 'MIXED_REPORT.md'
    sys.argv = [sys.argv[0], corpus, str(B / 'held_decided.json')]
    final_report.main()
    text = final_report.REPORT.read_text(encoding='utf-8')
    text = text.replace('# Final report (doc 04 section 18.5)', '# Mixed answers report (doc 04 sections 18.6-18.7)\n\n'
                        'The same criteria and scoring as FINAL_REPORT.md, with the answers of mixed_answer.py (separate '
                        'from the pipeline) in place of the pipeline\'s.', 1)
    text = text.replace('### The false positives (all from the main pipeline; the fallback made none)',
                        '### The false positives', 1)
    final_report.REPORT.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()

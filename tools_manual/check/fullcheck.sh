#!/bin/bash
# The full check of a change (docs/CONVERSION_FIX_PROMPTS.md, "The method"), run in a COPY of the repository that
# holds the change, compared with this repository's committed results.
#   usage: tools_manual/check/fullcheck.sh COPY_DIR NAME OUT_DIR
# Make the copy with everything, polyglot_logic/benchmark included:
#   mkdir COPY && tar cf - --exclude=.git . | (cd COPY && tar xf -)
# Writes OUT_DIR/NAME_result.txt: learnt answers that differ, fingerprints that differ, new-code right/wrong now and
# with the change, every held-out answer that changed; OUT_DIR/NAME_nodes.txt: tree nodes old against new.
# Any traceback in a log makes the run invalid (it says so). Takes about an hour.
set -u
M=$(cd "$(dirname "$0")/../.." && pwd); D=$1; N=$2; O=$3; C=$M/tools_manual/check
G1='data/TheAlgorithms-Python/**/*.py'; G2='data/rosetta/Task/*/*/*.*'
mkdir -p "$O"
[ -f "$O/n_base.json" ] || (cd "$M" && PYTHONPATH=.:tools_manual python3 $C/nodes_of.py "$O/n_base.json" "$G1" "$G2")
cd "$D" && PYTHONPATH=.:tools_manual python3 $C/nodes_of.py "$O/n_$N.json" "$G1" "$G2"
python3 $C/cmp_nodes.py "$O/n_base.json" "$O/n_$N.json" > "$O/${N}_nodes.txt"
cd "$D" && PYTHONPATH=. python3 ta_distinct.py data/TheAlgorithms-Python --index > "$O/${N}_index.log" 2>&1
cd "$D" && PYTHONPATH=. python3 $C/regen_components.py data/TheAlgorithms-Python > "$O/${N}_regen.log" 2>&1
cd "$D" && PYTHONPATH=. python3 eval_ta.py data/TheAlgorithms-Python --learn > "$O/${N}_learn.log" 2>&1
cd "$D" && PYTHONPATH=. python3 eval_ta.py data/TheAlgorithms-Python --run > "$O/${N}_run.log" 2>&1
cd "$D" && PYTHONPATH=. python3 eval_ta.py data/TheAlgorithms-Python --heldout data/rosetta > "$O/${N}_held.log" 2>&1
python3 - "$M" "$D" > "$O/${N}_result.txt" <<'PY'
import json, sys
M, D = sys.argv[1], sys.argv[2]
a = json.load(open(M + '/benchmark/ta_answers.json')); b = json.load(open(D + '/benchmark/ta_answers.json'))
d = [(k, a[k].get('got'), b[k].get('got'), b[k].get('why'), b[k].get('clash')) for k in a if a[k].get('got') != b[k].get('got')]
print('learnt differ', len(d)); [print('  ', x) for x in d]
s1 = json.load(open(M + '/benchmark/ta_signatures.json')); s2 = json.load(open(D + '/benchmark/ta_signatures.json'))
print('fingerprints differ', len([k for k in s1 if s1[k] != s2.get(k)]))
p = json.load(open(M + '/benchmark/ta_heldout.json')); h = json.load(open(D + '/benchmark/ta_heldout.json'))
def sc(X): return (sum(1 for v in X.values() if v.get('got') and v['got'] == v['task']),
                   sum(1 for v in X.values() if v.get('got') and v['got'] != v['task']))
print('new code right/wrong: now', sc(p), ' with the change', sc(h))
for k in p:
    if p[k].get('got') != h[k].get('got'):
        print('  ', k.replace('Task/', ''), p[k].get('got'), '->', h[k].get('got'), h[k]['why'], h[k].get('clash', ''))
PY
if grep -l Traceback "$O"/${N}_*.log; then echo "TRACEBACK in the logs above: this run is invalid" >> "$O/${N}_result.txt"; fi
cat "$O/${N}_result.txt"; head -1 "$O/${N}_nodes.txt"

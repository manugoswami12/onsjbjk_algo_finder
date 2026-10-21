"""Tree nodes of every file matching a glob, with the code of the current directory -> json (tools_manual/check)."""
import glob, json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path[:0] = ['.', 'tools_manual']
import learn_facts
def one(p):
    try:
        k, t = learn_facts.tree_facts(Path(p))
        return p, sorted(learn_facts.swipl_facts('tree_main', learn_facts.TREE_MAIN, k, t)) if t.strip() else []
    except Exception as e:
        return p, 'ERR ' + type(e).__name__
files = sorted(f for g in sys.argv[2:] for f in glob.glob(g, recursive=True))
with ThreadPoolExecutor(8) as pool:
    json.dump(dict(pool.map(one, files)), open(sys.argv[1], 'w'), indent=0)

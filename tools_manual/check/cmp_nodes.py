"""Old against new tree nodes: python cmp_nodes.py OLD.json NEW.json (tools_manual/check)."""
import json, sys
a, b = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
d = [k for k in a if a[k] != b.get(k)]
print(len(a), 'files,', len(d), 'changed')
for k in d: print(' ', k.split('/', 3)[-1], a[k], '->', b[k])

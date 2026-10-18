from collections import deque
def order(graph):
    indeg = {v: 0 for v in graph}
    for v in graph:
        for w in graph[v]:
            indeg[w] += 1
    queue = deque(v for v in graph if indeg[v] == 0)
    out = []
    while queue:
        v = queue.popleft()
        out.append(v)
        for w in graph[v]:
            indeg[w] -= 1
            if indeg[w] == 0:
                queue.append(w)
    return out

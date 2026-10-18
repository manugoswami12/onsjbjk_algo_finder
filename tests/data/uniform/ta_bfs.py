from collections import deque
def level_order(graph, start):
    seen = {start}
    order = []
    queue = deque([start])
    while queue:
        v = queue.popleft()
        order.append(v)
        for w in graph[v]:
            if w not in seen:
                seen.add(w)
                queue.append(w)
    return order

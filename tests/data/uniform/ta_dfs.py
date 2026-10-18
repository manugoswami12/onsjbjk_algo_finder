def walk(graph, start):
    seen = set()
    stack = [start]
    while stack:
        v = stack.pop()
        if v in seen:
            continue
        seen.add(v)
        for w in graph[v]:
            if w not in seen:
                stack.append(w)
    return seen

import heapq
def shortest(graph, src):
    dist = {src: 0}
    heap = [(0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        for v, w in graph[u]:
            if dist.get(v, float("inf")) > d + w:
                dist[v] = d + w
                heapq.heappush(heap, (d + w, v))
    return dist

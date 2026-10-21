def leftmost_leaf(depth):
    node = 0
    for _ in range(depth):
        node = node * 2 + 1
    return node

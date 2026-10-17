def walk(t):
    if t is not None:
        walk(t.left)
        print(t.value)
        walk(t.right)

def gen(n):
    a, b = 0, 1
    yield a
    for _ in range(n):
        yield b
        a, b = b, a + b

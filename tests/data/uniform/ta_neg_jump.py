import math
def jump(xs, x):
    n = len(xs)
    step = int(math.sqrt(n))
    prev = 0
    while prev < n and xs[min(step, n) - 1] < x:
        prev = step
        step += int(math.sqrt(n))
    for i in range(prev, min(step, n)):
        if xs[i] == x:
            return i
    return -1

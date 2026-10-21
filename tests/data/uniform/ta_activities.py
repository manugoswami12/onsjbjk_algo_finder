def choose(acts):
    acts = sorted(acts, key=lambda a: a[1])
    picked = [acts[0]]
    for i in range(1, len(acts)):
        if acts[i][0] >= picked[-1][1]:
            picked.append(acts[i])
    return picked

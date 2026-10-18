def orderings(nums, target):
    table = [0] * (target + 1)
    table[0] = 1
    for j in range(1, target + 1):
        for x in nums:
            if j >= x:
                table[j] += table[j - x]
    return table[target]

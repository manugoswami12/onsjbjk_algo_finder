def mixed(a, needle):
    for i in range(len(a)):
        for j in range(len(a)-i-1):
            if a[j] > a[j+1]:
                a[j], a[j+1] = a[j+1], a[j]
    lo = 0
    hi = len(a) - 1
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        if a[mid] == needle:
            return mid
        if a[mid] < needle:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

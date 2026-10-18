def leftmost(items, target):
    lo = 0
    hi = len(items) - 1
    found = -1
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        current = items[mid]
        if current == target:
            found = mid
            hi = mid - 1
        elif target < current:
            hi = mid - 1
        else:
            lo = mid + 1
    return found

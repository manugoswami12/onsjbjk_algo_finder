def present(items, x):
    if len(items) == 0:
        return False
    mid = len(items) // 2
    if items[mid] == x:
        return True
    if x < items[mid]:
        return present(items[:mid], x)
    else:
        return present(items[mid + 1:], x)

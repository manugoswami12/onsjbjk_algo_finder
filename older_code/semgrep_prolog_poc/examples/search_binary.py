"""Positive example; function name intentionally avoids 'binary_search'."""

def locate_item(values, target):
    lower = 0
    upper = len(values) - 1
    while lower <= upper:
        pivot = (lower + upper) // 2
        if values[pivot] == target:
            return pivot
        if values[pivot] < target:
            lower = pivot + 1
        else:
            upper = pivot - 1
    return -1

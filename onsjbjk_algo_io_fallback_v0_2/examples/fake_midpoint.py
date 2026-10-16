def not_search(arr, target):
    left = 0
    right = len(arr) - 1
    while left <= right:
        middle = (left + right) // 2
        left = middle + 1
    return -1

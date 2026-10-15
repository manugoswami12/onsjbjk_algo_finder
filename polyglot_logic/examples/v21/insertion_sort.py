def insertion_sort(items):
    for i in range(1, len(items)):
        key = items[i]
        while i > 0 and key < items[i - 1]:
            items[i] = items[i - 1]
            i -= 1
        items[i] = key
    return items

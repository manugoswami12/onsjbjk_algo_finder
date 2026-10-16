def find_item(values, target):
    for index in range(len(values)):
        if values[index] == target:
            return index
    return -1

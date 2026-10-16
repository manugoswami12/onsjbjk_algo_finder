def find_position(sequence, needle):
    start = 0
    end = len(sequence) - 1
    while start <= end:
        center = (start + end) // 2
        if sequence[center] == needle:
            return center
        if sequence[center] < needle:
            start = center + 1
        else:
            end = center - 1
    return -1

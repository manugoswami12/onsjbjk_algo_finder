def not_sort(data):
    for i in range(len(data)):
        if data[i] > 5:
            data[i] += 1
    return data

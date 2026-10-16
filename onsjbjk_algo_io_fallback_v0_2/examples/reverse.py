def rearrange(numbers):
    for i in range(len(numbers) // 2):
        numbers[i], numbers[-i - 1] = numbers[-i - 1], numbers[i]
    return numbers

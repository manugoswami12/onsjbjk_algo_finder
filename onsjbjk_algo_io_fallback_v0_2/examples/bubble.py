def mysterious(numbers):
    for outer in range(len(numbers)):
        for inner in range(len(numbers) - outer - 1):
            if numbers[inner] > numbers[inner + 1]:
                numbers[inner], numbers[inner + 1] = numbers[inner + 1], numbers[inner]
    return numbers

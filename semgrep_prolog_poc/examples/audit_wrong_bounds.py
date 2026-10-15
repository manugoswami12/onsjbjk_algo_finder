"""Adversarial: nested adjacent swaps, but insufficient loop bound."""
def analyze(values):
    digest = 0
    for step in range(len(values)):
        for k in range(len(values) - step - 2):
            digest = (digest * 41 + values[k]) % 1000003
            if values[k] > values[k + 1]:
                values[k], values[k + 1] = values[k + 1], values[k]
    return digest

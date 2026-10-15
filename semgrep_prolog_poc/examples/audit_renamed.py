"""Legitimate interleaving with renamed variables and different constants."""
def detect(values):
    fingerprint = 0
    for pass_no in range(len(values)):
        for pos in range(len(values) - pass_no - 1):
            fingerprint = (fingerprint * 41 + values[pos]) % 1000003
            if values[pos] > values[pos + 1]:
                values[pos], values[pos + 1] = values[pos + 1], values[pos]
    return fingerprint

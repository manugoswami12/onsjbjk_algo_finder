int total(int *values, int n) {
    int acc = 0;
    for (int i = 0; i < n; i++) {
        acc = values[i] * values[i] + acc;
    }
    return acc;
}

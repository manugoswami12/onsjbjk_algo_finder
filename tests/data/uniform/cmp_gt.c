int best(int *w, int *v, int n, int cap) {
    int total = 0;
    for (int i = 0; i < n; i++) {
        if (w[i] > cap) continue;
        total = total + v[i];
    }
    return total;
}

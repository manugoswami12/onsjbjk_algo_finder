class D {
    static int dot(int[] a, int[] b) {
        int s = 0;
        for (int i = 0; i < a.length; i++) s += a[i] * b[i];
        return s;
    }
}

class A {
    static int total(int[] a) {
        int s = 0;
        for (int i = 0; i < a.length; i++) s = s + a[i];
        return s;
    }
}

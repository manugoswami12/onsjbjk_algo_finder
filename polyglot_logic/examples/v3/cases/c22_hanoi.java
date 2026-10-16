class H {
    static void move(int n, int from, int to, int via) {
        if (n == 0) return;
        move(n - 1, from, via, to);
        System.out.println(from + " -> " + to);
        move(n - 1, via, to, from);
    }
}

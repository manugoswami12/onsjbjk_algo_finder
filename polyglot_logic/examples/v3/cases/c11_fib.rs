fn fib(n: u64) -> u64 {
    let (mut a, mut b) = (0, 1);
    for _ in 0..n {
        let t = a + b;
        a = b;
        b = t;
    }
    a
}

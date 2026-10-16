fn sort(v: &mut Vec<i32>) {
    let n = v.len();
    for i in 0..n {
        let mut m = i;
        for j in (i + 1)..n {
            if v[j] < v[m] { m = j; }
        }
        v.swap(i, m);
    }
}

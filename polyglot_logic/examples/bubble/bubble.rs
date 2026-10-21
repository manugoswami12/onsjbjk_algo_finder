pub fn bubble_sort(v: &mut Vec<i64>) {
    let n = v.len();
    for i in 0..n {
        for j in 0..n - i - 1 {
            if v[j] > v[j + 1] {
                v.swap(j, j + 1);
            }
        }
    }
}

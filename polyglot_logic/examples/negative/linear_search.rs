pub fn linear_search(v: &[i64], target: i64) -> i64 {
    let mut i: usize = 0;
    while i < v.len() {
        if v[i] == target {
            return i as i64;
        }
        i += 1;
    }
    -1
}

pub fn binary_search(v: &[i64], target: i64) -> i64 {
    let mut low: i64 = 0;
    let mut high: i64 = v.len() as i64 - 1;
    while low <= high {
        let mid = (low + high) / 2;
        if v[mid as usize] == target {
            return mid;
        } else if v[mid as usize] < target {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    -1
}

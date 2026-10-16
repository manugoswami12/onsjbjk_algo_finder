fn roman(mut n: u32) -> String {
    let vals = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1];
    let syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"];
    let mut out = String::new();
    for i in 0..vals.len() {
        while n >= vals[i] {
            n -= vals[i];
            out.push_str(syms[i]);
        }
    }
    out
}

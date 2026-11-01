use std::io::Cursor;
fn main() {
    let a: Vec<String> = std::env::args().collect();
    let data = std::fs::read(&a[1]).unwrap();
    let off: usize = a[3].parse().unwrap();
    let len: usize = a[4].parse().unwrap();
    let mut out = vec![0u8; len];
    let mut ex = oozextract::Extractor::new();
    let mut cur = Cursor::new(&data[off..]);
    let n = ex.read(&mut cur, &mut out).unwrap();
    std::fs::write(&a[2], &out[..n]).unwrap();
    println!("{}", n);
}

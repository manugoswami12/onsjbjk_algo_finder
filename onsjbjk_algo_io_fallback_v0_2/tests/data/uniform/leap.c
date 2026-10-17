int leap(int y) { return !(y & (y % 100 ? 3 : 15)); }

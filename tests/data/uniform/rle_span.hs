encode :: String -> [(Int, Char)]
encode [] = []
encode (x : xs) = let (run, rest) = span (x ==) xs in (1 + length run, x) : encode rest

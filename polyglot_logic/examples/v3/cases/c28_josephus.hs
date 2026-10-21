josephus :: Int -> Int -> Int
josephus 1 _ = 0
josephus n k = (josephus (n - 1) k + k) `mod` n

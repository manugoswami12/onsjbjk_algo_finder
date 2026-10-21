safe :: Int -> [Int] -> Bool
safe q qs = not (q `elem` qs || q `elem` up qs || q `elem` down qs)
  where
    up xs = zipWith (+) xs [1 ..]
    down xs = zipWith (-) xs [1 ..]

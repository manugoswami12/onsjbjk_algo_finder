module Hash where

import Data.Char (ord)

polyHash :: String -> Int
polyHash = foldl step 0
  where step h c = (h * 31 + ord c) `mod` 1000003

polyHash2 :: String -> Int
polyHash2 s = foldl (\h c -> (h * 31 + fromEnum c) `mod` 1000003) 0 s

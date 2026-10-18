import Data.Char (chr, ord)
shiftWith :: Char -> Int -> Char -> Char
shiftWith b k c = chr (fromIntegral (b' + (c' - b' + k) `mod` 26))
  where b' = ord b
        c' = ord c

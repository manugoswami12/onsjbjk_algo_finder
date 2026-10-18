import Data.Char (chr, ord)
shift :: Int -> Char -> Char
shift k c = chr . ((+) 65 . flip mod 26 . subtract 65) $ (k + ord c)

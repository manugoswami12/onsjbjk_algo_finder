(defun edit (x y)
  (if (or (zerop x) (zerop y))
      (+ x y)
      (min (+ (edit (1- x) y) 1) (+ (edit x (1- y)) 1))))

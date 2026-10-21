(defun mmul (a b)
  (mapcar (lambda (row) (apply #'mapcar (lambda (&rest col) (apply #'+ (mapcar #'* row col))) b)) a))

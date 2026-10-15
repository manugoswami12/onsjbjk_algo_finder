(defun binary-search (a target)
  (let ((low 0) (high (- (length a) 1)))
    (loop while (<= low high) do
      (let ((mid (floor (+ low high) 2)))
        (cond ((= (aref a mid) target) (return-from binary-search mid))
              ((< (aref a mid) target) (setf low (+ mid 1)))
              (t (setf high (- mid 1))))))
    -1))

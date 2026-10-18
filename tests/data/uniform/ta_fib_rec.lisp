(defun seq (n) (if (< n 2) n (+ (seq (- n 1)) (seq (- n 2)))))

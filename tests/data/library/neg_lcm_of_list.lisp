(defun lcm-list (xs)
  (let ((r 1))
    (dolist (x xs r)
      (setf r (lcm r x)))))

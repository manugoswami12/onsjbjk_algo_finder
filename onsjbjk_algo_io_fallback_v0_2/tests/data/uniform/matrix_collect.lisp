(defun matmul (a b n)
  (loop for i below n
        collect (loop for j below n
                      collect (let ((s 0))
                                (loop for k below n
                                      do (setf s (+ s (* (aref a i k) (aref b k j)))))
                                s))))

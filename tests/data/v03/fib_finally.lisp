(defun fib-loop (n)
  (if (< n 2) n
      (let ((ab (list 1 0)))
        (loop for i from 2 upto n do
              (setf ab (list (+ (first ab) (second ab)) (first ab)))
              finally (return (first ab))))))

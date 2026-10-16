(defun my-gcd (a b)
  (loop while (/= b 0) do
    (let ((r (mod a b)))
      (setf a b)
      (setf b r)))
  a)

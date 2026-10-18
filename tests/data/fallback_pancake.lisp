(defun rev-prefix (v k) (setf (subseq v 0 k) (reverse (subseq v 0 k))))
(defun psort (v)
  (loop for i from (length v) downto 2
        for p = (position (apply #'max (subseq v 0 i)) v)
        do (rev-prefix v (1+ p)) (rev-prefix v i))
  v)
(defun maxpos (v) (loop for i from (length v) downto 2 collect (position (apply #'max (subseq v 0 i)) v)))

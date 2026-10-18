(defun ins (x s p) (cond ((null s) (list x)) ((funcall (complement p) (car s) x) (cons x s)) (t (cons (car s) (ins x (cdr s) p)))))
(defun risort (s &optional (p #'<)) (if (cdr s) (ins (car s) (risort (cdr s) p) p) s))
(defun cpy (s) (if (null s) nil (cons (car s) (cpy (cdr s)))))
(defun rcopy (s) (if (cdr s) (cpy s) s))

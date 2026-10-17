(defun cut (pred list) (let ((tail (member-if-not pred list))) (values (ldiff list tail) tail)))
(defun below (x) (lambda (y) (< y x)))
(defun put (list elt) (multiple-value-bind (left right) (cut (below elt) list) (append left (list elt) right)))
(defun fsort (list) (reduce #'put list :initial-value nil))

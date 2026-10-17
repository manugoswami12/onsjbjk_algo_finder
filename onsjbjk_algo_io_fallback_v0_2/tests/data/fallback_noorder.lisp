(defun front (list elt) (append (list elt) list))
(defun fcopy (list) (reduce #'front list :initial-value nil))

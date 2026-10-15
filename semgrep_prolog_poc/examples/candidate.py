"""AP9 additional renamed binary-search candidate.

Use this with RUN_AP9_REFERENCE.cmd. This is an alpha-renamed positive
control, not a semantically different algorithm implementation.
"""


def find_position(sequence, needle):
    start = 0
    end = len(sequence) - 1
    while start <= end:
        center = (start + end) // 2
        if sequence[center] == needle:
            return center
        if sequence[center] < needle:
            start = center + 1
        else:
            end = center - 1
    return -1

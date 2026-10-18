"""Negative control: linear search must not be labelled binary search."""

def locate_item(values, target):
    for pos, value in enumerate(values):
        if value == target:
            return pos
    return -1

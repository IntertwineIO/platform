#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from itertools import zip_longest


def average(values, weights=None):
    """
    Average

    I/O:
    values:         iterable of numeric values
    weights=None:   iterable of numeric weights to apply to values
    return:         average of values, optionally weighted
    raise:          ValueError if not same number of values and weights
    raise:          ZeroDivisionError if weights sum to 0
    raise:          TypeError if any value or weight is non-numeric
    """
    numerator = denominator = 0

    if weights is None:
        for denominator, value in enumerate(values, start=1):
            numerator += value
        return numerator / denominator

    try:
        for value, weight in zip_longest(values, weights):
            numerator += value * weight
            denominator += weight
    except TypeError as e:
        if len(values) != len(weights):
            raise ValueError('There must be the same number of values and weights') from e
        raise
    return numerator / denominator

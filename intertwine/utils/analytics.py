#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from itertools import zip_longest


def weighted_average(values, weights):
    numerator = sum(value * weight for (value, weight) in zip_longest(values, weights))
    denominator = sum(weights)
    return numerator / denominator

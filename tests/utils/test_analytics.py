#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest

from intertwine.utils.analytics import weighted_average
from intertwine.utils.tools import is_child_class


@pytest.mark.unit
@pytest.mark.parametrize(
    ('idx', 'values',           'weights',                 'check'),
    [
     (0,    [0, 1],             [1, 0],                    0),
     (1,    [1, 2],             [1, 0],                    1),
     (2,    [1, 2],             [0, 2],                    2),
     (3,    [1, 4],             [1, 2],                    3),
     (4,    [2, 8],             [2, 1],                    4),
     (5,    [3, 6, 9],          [2, 0, 1],                 5),
     (6,    [3, 6, 9],          [1, 1, 1],                 6),
     (7,    [3, 6, 9],          [0, 2, 1],                 7),
     (8,    [1, 2, 3],          [1, 1],                    TypeError),
     (9,    [1, 2],             [1, 1, 1],                 TypeError),
     ])
def test_weighted_average(idx, values, weights, check):
    if is_child_class(check, Exception):
        with pytest.raises(check):
            weighted_average(values, weights)
    else:
        weighted_average(values, weights)

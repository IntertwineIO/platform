#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
from itertools import tee

from intertwine.utils.analytics import average
from intertwine.utils.duck_typing import isiterator
from intertwine.utils.tools import is_child_class


@pytest.mark.unit
@pytest.mark.parametrize(
    ('idx', 'values',                   'weights',                 'check'),
    [
     (0,    [0, 1],                     [1, 0],                    0),
     (1,    [1, 2],                     [1, 0],                    1),
     (2,    [1, 2],                     [0, 1],                    2),
     (3,    [1, 4],                     [1, 2],                    3),
     (4,    [2, 3, 5],                  [1, 2, 4],                 4),
     (5,    [3, 5, 7],                  None,                      5),
     (6,    (i * 6 for i in range(3)),  None,                      6),
     (7,    (i * 7 for i in range(3)),  [1, 1, 1],                 7),
     (8,    (i * 8 for i in range(3)),  (i for i in [1] * 3),      8),
     (9,    [6, 9, 12],                 (i for i in [1] * 3),      9),
     (10,   [1, 2, 3],                  [1, 1],                    ValueError),
     (11,   [1, 2],                     [1, 1, 1],                 ValueError),
     (12,   [1, 2],                     [0],                       ValueError),
     (13,   [1, 2],                     ['a'],                     ValueError),
     (14,   [1, 2],                     [0, 0],                    ZeroDivisionError),
     (15,   [],                         [],                        ZeroDivisionError),
     (16,   [1, 2],                     [1, 'a'],                  TypeError),
     (17,   [1, 'a'],                   [1, 1],                    TypeError),
     (18,   None,                       [1, 1],                    TypeError),
     (19,   None,                       None,                      TypeError),
     ])
def test_average(idx, values, weights, check):
    if is_child_class(check, Exception):
        with pytest.raises(check):
            average(values, weights)
    else:
        if weights is None:
            values, values2 = tee(values, 2) if isiterator(values) else (values, values)
            assert average(values2) == check
        assert average(values, weights) == check

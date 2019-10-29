# -*- coding: utf-8 -*-
import pytest
from collections import namedtuple
from enum import Enum
from itertools import tee

from intertwine.utils.duck_typing import (
    iscollection, isiterable, isiterator, isnamedtuple, isnonstringsequence, issequence)


MyNamedTuple = namedtuple('MyNamedTuple', 'first second third')


class CrosswalkSignal(Enum):
    DONT_WALK = "Don't Walk"
    WALK = 'Walk'
    THREE = 3
    TWO = 2
    ONE = 1


@pytest.mark.unit
@pytest.mark.parametrize(
    #          1          2              3              4
    'func, int_check, enum_check, enum_class_check, str_check, '
    #     5           6               7              8          9
    'list_check, tuple_check, namedtuple_check, dict_check, set_check, '
    #     10            11               12
    'range_check, iterator_check, generator_check',
    [
     #                     1  2  3  4  5  6  7  8  9 10 11 12
     (iscollection,        0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0),
     (isiterable,          0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
     (isiterator,          0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1),
     (isnamedtuple,        0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
     (isnonstringsequence, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0),
     (issequence,          0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0),
    ])
def test_duck_type_checkers(
        func, int_check, enum_check, enum_class_check, str_check,
        list_check, tuple_check, namedtuple_check, dict_check, set_check,
        range_check, iterator_check, generator_check):
    """Test duck-type checker functions"""
    assert bool(int_check) is func(0)
    assert bool(int_check) is func(42)
    assert bool(enum_check) is func(CrosswalkSignal.WALK)
    assert bool(enum_class_check) is func(CrosswalkSignal)
    assert bool(str_check) is func('')
    assert bool(str_check) is func('Holy Hand Grenade')
    assert bool(list_check) is func([])
    assert bool(list_check) is func([1, 2, 3])
    assert bool(tuple_check) is func(())
    assert bool(tuple_check) is func(('a', 'b', 'c'))
    assert bool(namedtuple_check) is func(MyNamedTuple('alpha', 'beta', 'gamma'))
    assert bool(dict_check) is func({})
    assert bool(dict_check) is func({'a': 1, 'b': 2, 'c': 3})
    assert bool(set_check) is func(set())
    assert bool(set_check) is func({-1, 0, 1})
    assert bool(range_check) is func(range(0))
    assert bool(range_check) is func(range(3))
    assert bool(iterator_check) is func(iter(range(0)))
    assert bool(iterator_check) is func(iter(range(3)))
    generator = (x ** 2 for x in range(3))
    gen_x, gen_y = tee(generator, 2)
    assert bool(generator_check) is func(gen_x)
    assert list(gen_x) == list(gen_y), f'{func} consumes the generator!'
    assert bool(generator_check) is func(x for x in range(0))

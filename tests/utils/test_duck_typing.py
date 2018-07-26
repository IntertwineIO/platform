#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
from collections import namedtuple
from enum import Enum

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
    #          1              2               3          4
    'func, int_check, enum_option_check, enum_check, str_check, '
    #     5           6               7              8          9            10
    'list_check, tuple_check, namedtuple_check, dict_check, set_check, generator_check', [
    #                       1      2      3      4      5      6      7      8      9      10
    (iscollection,        False, False, True,  False, True,  True,  True,  True,  True,  False),
    (isiterable,          False, False, True,  True,  True,  True,  True,  True,  True,  True),
    (isiterator,          False, False, False, False, False, False, False, False, False, True),
    (isnamedtuple,        False, False, False, False, False, False, True,  False, False, False),
    (isnonstringsequence, False, False, True,  False, True,  True,  True,  False, False, False),
    (issequence,          False, False, True,  True,  True,  True,  True,  False, False, False),
])
def test_duck_type_checkers(
    session, func, int_check, enum_option_check, enum_check, str_check,
    list_check, tuple_check, namedtuple_check, dict_check, set_check, generator_check):
    """Test duck-type checker functions"""
    assert int_check is func(0)
    assert int_check is func(42)
    assert enum_option_check is func(CrosswalkSignal.WALK)
    assert enum_check is func(CrosswalkSignal)
    assert str_check is func('')
    assert str_check is func('Holy Hand Grenade')
    assert list_check is func([])
    assert list_check is func([1, 2, 3])
    assert tuple_check is func(())
    assert tuple_check is func(('a', 'b', 'c'))
    assert namedtuple_check is func(MyNamedTuple('alpha', 'beta', 'gamma'))
    assert dict_check is func({})
    assert dict_check is func({'a': 1, 'b': 2, 'c': 3})
    assert set_check is func(set())
    assert set_check is func({-1, 0, 1})
    assert generator_check is func(x for x in range(0))
    assert generator_check is func(x ** 2 for x in range(3))

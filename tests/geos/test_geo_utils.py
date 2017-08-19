#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import pytest
import sys
from decimal import Decimal

from intertwine.geos.utils import Area, Coordinate

# Python version compatibilities
if sys.version_info >= (3,):
    long = int
    unicode = str


def perform_core_quantized_interactions(cls, number):
    '''Test core interactions for QuantizedDecimal class'''
    precision = cls.DEFAULT_PRECISION
    multiplier = Decimal(10) ** precision
    decimal_value = Decimal(number).quantize(1 / multiplier)
    dequantized_value = int(decimal_value * multiplier)
    inst = cls(number)

    # Test properties and repr
    assert inst.precision == precision
    assert inst.value == decimal_value
    assert eval(repr(inst)) == inst

    # Test dequantize/requantize
    dequantized = inst.dequantize()
    assert dequantized == dequantized_value
    assert cls.requantize(dequantized) == inst
    assert cls(dequantized, requantize=True) == inst

    # Test casts
    assert cls.cast_to_decimal(number) == decimal_value
    assert cls.cast(number) == inst
    assert cls.cast(inst) is inst


@pytest.mark.unit
@pytest.mark.parametrize('number', [
    str('0.123456'),
    float(987654321.123456),
    int(512),
    long(98765432109876543210),
    0
])
def test_area_core_interactions(session, number):
    '''Test core Area interactions'''
    perform_core_quantized_interactions(Area, number)


@pytest.mark.unit
@pytest.mark.parametrize('number', [
    str('0.1234567890'),
    float(12.1234567890),
    int(-90),
    long(90),
    0
])
def test_coordinate_core_interactions(session, number):
    '''Test core Coordinate interactions'''
    perform_core_quantized_interactions(Coordinate, number)

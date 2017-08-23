#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import sys
from decimal import Decimal

# Python version compatibilities
if sys.version_info < (3,):
    INT_TYPES = (int, long)  # noqa: ignore=F821
else:
    INT_TYPES = (int,)
    long = int
    unicode = str


class QuantizedDecimal(object):
    '''
    QuantizedDecimal

    A utility class for decimals with prescribed precision that are
    stored as integers. Here, "precision" is defined to be the number of
    decimal places to which the decimals should be quantized.

    When precision is not specified, a default of 2 is used. To change
    the default, simply subclass QuantizedDecimal and override the
    DEFAULT_PRECISION.

    All comparison and mathematical operators are supported. Note that
    most operators work by using the Decimal value and then converting
    the result to QuantizedDecimal. The only exception is divmod, which
    uses the Decimal value and returns a tuple without modification.

    Caution: iterative application of operators on QuantizedDecimals may
    lead to rounding errors since the result is automatically quantized.
    If multiple operators need to be applied in succession without
    rounding, use the (Decimal) value of all QuantizedDecimals.
    '''

    DEFAULT_PRECISION = 2

    _multipliers = {}

    @property
    def value(self):
        '''Return the value, a Decimal quantized with the precision'''
        return self._value

    @value.setter
    def value(self, number):
        '''Set the Decimal value quantized with the default precision'''
        self._value = self.quantize(number, self.precision)

    @property
    def precision(self):
        '''Return the precision, an integer'''
        return self._precision

    @precision.setter
    def precision(self, number):
        '''Set the precision and use it to quantize the Decimal value'''
        precision = self._get_precision(number)
        try:
            self._value = self.quantize(self.value, precision)
        except AttributeError:
            pass  # During __init__ self.value has not yet been defined
        self._precision = precision

    def dequantize(self):
        '''Move decimal point to the right and return the integer'''
        return int(self.value * self._get_multiplier(self.precision))

    @classmethod
    def requantize(cls, integer, precision=None):
        '''Move decimal point left by precision and return Decimal'''
        precision = cls._get_precision(precision)
        raw_decimal = Decimal(integer) / cls._get_multiplier(precision)
        return cls.quantize(raw_decimal, precision)

    @classmethod
    def quantize(cls, number, precision=None):
        '''Cast to Decimal and quantize with precision (or default)'''
        raw_decimal = cls.cast_to_decimal(number)
        precision = cls._get_precision(precision)
        return raw_decimal.quantize(cls._get_quant(precision))

    @classmethod
    def cast_to_decimal(cls, number):
        '''Cast to Decimal'''
        if isinstance(number, QuantizedDecimal):
            return number.value
        if isinstance(number, Decimal):
            return number
        return Decimal(number)

    @classmethod
    def _get_multiplier(cls, precision):
        try:
            return cls._multipliers[precision]
        except KeyError:
            multiplier = Decimal(10) ** Decimal(precision)
            cls._multipliers[precision] = multiplier
            return multiplier

    @classmethod
    def _get_quant(cls, precision):
        multiplier = cls._get_multiplier(precision)
        return 1 / multiplier

    @classmethod
    def _get_precision(cls, precision=None, inst=None):
        if precision is not None:
            return precision
        try:
            return inst.precision
        except AttributeError:
            return cls.DEFAULT_PRECISION

    @classmethod
    def cast(cls, number, precision=None):
        '''Cast to QuantizedDecimal of given precision, if not already one'''
        return (number if isinstance(number, cls) and
                (precision is None or number.precision == precision)
                else cls(number, precision))

    def __init__(self, number, precision=None, requantize=False):
        self.precision = precision  # Must precede value
        self.value = (self.requantize(number, precision) if requantize
                      else number)

    def __repr__(self):
        precision = self.precision
        return "{cls}('{number}'{precision_clause})".format(
            cls=self.__class__.__name__, number=self.value,
            precision_clause=(', ' + str(precision)
                              if precision != self.DEFAULT_PRECISION else ''))

    def __str__(self):
        return str(self.value)

    # Comparison Operators

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return self.value != other

    def __lt__(self, other):
        return self.value < other

    def __le__(self, other):
        return self.value <= other

    def __gt__(self, other):
        return self.value > other

    def __ge__(self, other):
        return self.value >= other

    # Left-Variant Mathematical Operators

    def __add__(self, other):
        return self.__class__(self.value + other, self.precision)

    def __sub__(self, other):
        return self.__class__(self.value - other, self.precision)

    def __mul__(self, other):
        return self.__class__(self.value * other, self.precision)

    def __truediv__(self, other):
        return self.__class__(self.value / other, self.precision)

    def __floordiv__(self, other):
        return self.__class__(self.value // other, self.precision)

    def __div__(self, other):
        return self.__class__(self.value.__div__(other), self.precision)

    def __mod__(self, other):
        return self.__class__(self.value % other, self.precision)

    def __divmod__(self, other):
        return divmod(self.value, other)  # return tuple of Decimals

    def __pow__(self, other, modulo=None):
        return self.__class__(pow(self.value, other, modulo), self.precision)

    # Right-Variant Mathematical Operators

    def __radd__(self, other):
        return self.__class__(other + self.value, self.precision)

    def __rsub__(self, other):
        return self.__class__(other - self.value, self.precision)

    def __rmul__(self, other):
        return self.__class__(other * self.value, self.precision)

    def __rtruediv__(self, other):
        return self.__class__(other / self.value, self.precision)

    def __rfloordiv__(self, other):
        return self.__class__(other // self.value, self.precision)

    def __rdiv__(self, other):
        return self.__class__(self.value.__rdiv__(other), self.precision)

    def __rmod__(self, other):
        return self.__class__(other % self.value, self.precision)

    def __rdivmod__(self, other):
        return divmod(other, self.value)  # return tuple of Decimals

    def __rpow__(self, other):
        return self.__class__(pow(other, self.value), self.precision)

    # In-Place Mathematical Operators

    def __iadd__(self, other):
        self.value += other
        return self

    def __isub__(self, other):
        self.value -= other
        return self

    def __imul__(self, other):
        self.value *= other
        return self

    def __itruediv__(self, other):
        self.value /= other
        return self

    def __ifloordiv__(self, other):
        self.value //= other
        return self

    def __idiv__(self, other):
        self.value.__idiv__(other)
        return self

    def __imod__(self, other):
        self.value %= other
        return self

    def __ipow__(self, other):
        self.value **= other
        return self

    # Unary Mathematical Operators

    def __abs__(self):
        return self.__class__(abs(self.value), self.precision)

    def __neg__(self):
        return self.__class__(-self.value, self.precision)

    def __pos__(self):
        return self.__class__(+self.value, self.precision)

    # Number Type Casts

    def __complex__(self):
        return complex(self.value)

    def __float__(self):
        return float(self.value)

    def __int__(self):
        return int(self.value)

    def __long__(self):
        return long(self.value)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import sys
from collections import namedtuple
from decimal import Decimal

# Python version compatibilities
if sys.version_info < (3,):
    INT_TYPES = (int, long)  # noqa: ignore=F821
else:
    INT_TYPES = (int,)
    long = int
    unicode = str


class QuantizedDecimal(object):

    MAX_PRECISION = 10
    DEFAULT_PRECISION = 2

    _multipliers = {n: Decimal('1{}'.format('0' * n))
                    for n in range(MAX_PRECISION + 1)}

    _quants = {n: Decimal('0.{}1'.format('0' * (n - 1))) if n else Decimal(1)
               for n in range(MAX_PRECISION + 1)}

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, number):
        self._value = self.cast_to_decimal(number, self.precision)

    @property
    def precision(self):
        return self._precision

    @precision.setter
    def precision(self, number):
        self._precision = self.get_precision(number)
        try:
            self._value = self.quantize_this(self.value, inst=self)
        except AttributeError:
            pass  # During __init__

    def dequantize(self):
        return int(self.value * self.get_multiplier(inst=self))

    @classmethod
    def requantize(cls, integer, precision=None):
        raw_decimal = Decimal(integer) / cls.get_multiplier(precision)
        return cls.cast_to_decimal(raw_decimal, precision)

    @classmethod
    def cast_to_decimal(cls, number, precision=None):
        raw_decimal = (number.value if isinstance(number, QuantizedDecimal)
                       else Decimal(number))
        return cls.quantize_this(raw_decimal, precision)

    @classmethod
    def quantize_this(cls, number, precision=None, inst=None):
        precision = cls.get_precision(precision, inst)
        return number.quantize(cls.get_quant(precision, inst))

    @classmethod
    def get_multiplier(cls, precision=None, inst=None):
        precision = cls.get_precision(precision, inst)
        return cls._multipliers[precision]

    @classmethod
    def get_quant(cls, precision=None, inst=None):
        precision = cls.get_precision(precision, inst)
        return cls._quants[precision]

    @classmethod
    def get_precision(cls, precision=None, inst=None):
        try:
            return inst.precision
        except AttributeError:
            if precision is not None:
                cls._validate_precision(precision)
                return precision
            return cls.DEFAULT_PRECISION

    @classmethod
    def _validate_precision(cls, precision):
        if precision not in cls._quants:
            raise ValueError('Precision must be integer 0-{}, inclusive'
                             .format(cls.MAX_PRECISION))
        return precision

    @classmethod
    def cast(cls, number):
        return number if isinstance(number, cls) else cls(number)

    def __init__(self, number, precision=None, requantize=False):
        self.precision = precision  # Must precede value
        self.value = self.requantize(number) if requantize else number

    def __repr__(self):
        return '{cls}({number}, {precision})'.format(
            cls=self.__class__.__name__, number=self.value,
            precision=self.precision)

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
        return self.__class__(divmod(self.value, other), self.precision)

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
        return self.__class__(divmod(other, self.value), self.precision)

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

    def __neg__(self):
        return self.__class__(-self.value, self.precision)

    def __pos__(self):
        return self.__class__(+self.value, self.precision)

    def __abs__(self):
        return self.__class__(abs(self.value), self.precision)

    # Cast Mathematical Operators

    def __complex__(self):
        return complex(self.value)

    def __int__(self):
        return int(self.value)

    def __long__(self):
        return long(self.value)

    def __float__(self):
        return float(self.value)


class Area(QuantizedDecimal):

    DEFAULT_PRECISION = 6  # square meters to square kilometers

    def __repr__(self):
        return 'Area({})'.format(self.value)


class Coordinate(QuantizedDecimal):

    DEFAULT_PRECISION = 7  # 7: 11 mm; 6: 0.11 m (https://goo.gl/7qq5sR)

    def __repr__(self):
        return 'Coordinate({})'.format(self.value)


class GeoLocation(object):

    LATITUDE = 'latitude'
    LONGITUDE = 'longitude'
    COORDINATES = (LATITUDE, LONGITUDE)

    Coordinates = namedtuple('Coordinates', COORDINATES)

    @property
    def latitude(self):
        return self._latitude

    @latitude.setter
    def latitude(self, value):
        self._latitude = Coordinate.cast(value)

    @property
    def longitude(self):
        return self._longitude

    @longitude.setter
    def longitude(self, value):
        self._longitude = Coordinate.cast(value)

    @property
    def coordinates(self):
        return self.Coordinates(self.latitude, self.longitude)

    @coordinates.setter
    def coordinates(self, values):
        self.latitude, self.longitude = values  # Invoke setters

    @property
    def values(self):
        return self.Coordinates(self.latitude.value, self.longitude.value)

    def dequantize(self):
        return self.Coordinates(
            self.latitude.dequantize(), self.longitude.dequantize())

    @classmethod
    def combine_coordinates(cls, *weighted_geo_locations):
        total_latitude = total_longitude = total_weight = 0

        for geo_location, weight in weighted_geo_locations:
            latitude, longitude = geo_location.values
            weight = QuantizedDecimal.cast_to_decimal(weight)
            total_latitude += latitude * weight
            total_longitude += longitude * weight
            total_weight += weight

        total_latitude /= total_weight
        total_longitude /= total_weight
        return cls(total_latitude, total_longitude)

    @classmethod
    def cast(cls, value):
        return value if isinstance(value, cls) else cls(value)

    def __init__(self, latitude, longitude):
        self.latitude = latitude  # Invoke setter
        self.longitude = longitude  # Invoke setter

    def __repr__(self):
        return 'GeoLocation({}, {})'.format(*self.coordinates)

    def __str__(self):
        return '(latitude={}, longitude={})'.format(*self.coordinates)

    # Container Methods

    def __getitem__(self, key):
        field = self.COORDINATES[key] if isinstance(key, INT_TYPES) else key
        if isinstance(field, (str, unicode)) and field[0] == '_':
            raise AttributeError('Attempting to access private member')
        return getattr(self, field)

    def __setitem__(self, key, value):
        field = self.COORDINATES[key] if isinstance(key, INT_TYPES) else key
        if isinstance(field, (str, unicode)) and field[0] == '_':
            raise AttributeError('Attempting to access private member')
        setattr(self, field, value)

    def __iter__(self):
        for coordinate in self.coordinates:
            yield coordinate

    # Comparison Operators

    def _operate(self, operator, other):
        try:
            return operator(other.coordinates)
        except AttributeError:
            return operator(other)

    def __eq__(self, other):
        return self._operate(self.coordinates.__eq__, other)

    def __ne__(self, other):
        return self._operate(self.coordinates.__ne__, other)

    def __lt__(self, other):
        return self._operate(self.coordinates.__lt__, other)

    def __le__(self, other):
        return self._operate(self.coordinates.__le__, other)

    def __gt__(self, other):
        return self._operate(self.coordinates.__gt__, other)

    def __ge__(self, other):
        return self._operate(self.coordinates.__ge__, other)

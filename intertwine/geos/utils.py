#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import sys
from collections import namedtuple

from intertwine.utils.quantized import QuantizedDecimal

# Python version compatibilities
if sys.version_info < (3,):
    INT_TYPES = (int, long)  # noqa: ignore=F821
else:
    INT_TYPES = (int,)
    long = int
    unicode = str


class Area(QuantizedDecimal):

    DEFAULT_PRECISION = 6  # square meters to square kilometers

    def __repr__(self):
        return "Area('{}')".format(self.value)


class Coordinate(QuantizedDecimal):

    DEFAULT_PRECISION = 7  # 7: 11 mm; 6: 0.11 m (https://goo.gl/7qq5sR)

    def __repr__(self):
        return "Coordinate('{}')".format(self.value)


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
    def combine_locations(cls, *weighted_locations):
        weighted_coordinates = (
            (geo_location.values, weight)
            for geo_location, weight in weighted_locations)

        return cls(*cls.combine_coordinates(*weighted_coordinates))

    @classmethod
    def combine_coordinates(cls, *weighted_coordinates):
        total_latitude = total_longitude = total_weight = 0

        for coordinate_values, weight in weighted_coordinates:
            latitude, longitude = coordinate_values
            weight = QuantizedDecimal.cast_to_decimal(weight)
            total_latitude += latitude * weight
            total_longitude += longitude * weight
            total_weight += weight

        total_latitude /= total_weight
        total_longitude /= total_weight
        return cls.Coordinates(total_latitude, total_longitude)

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

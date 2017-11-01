#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import sys
from collections import namedtuple
from past.builtins import basestring

import pendulum
from timezonefinder import TimezoneFinder

from intertwine.utils.quantized import QuantizedDecimal

# Python version compatibilities
if sys.version_info < (3,):
    INT_TYPES = (int, long)  # noqa: ignore=F821
else:
    INT_TYPES = (int,)


class Area(QuantizedDecimal):

    DEFAULT_PRECISION = 6  # square meters to square kilometers


class Coordinate(QuantizedDecimal):

    DEFAULT_PRECISION = 7  # 7: 11 mm; 6: 0.11 m (https://goo.gl/7qq5sR)


class GeoLocation(object):
    '''
    GeoLocation

    A utility class for working with coordinates (latitude & longitude).

    GeoLocation utilizes the Coordinates namedtuple as a light-weight
    representation of latitude and longitude pairs. This is used to wrap
    the latitude/longitude returned from coordinates(), values(),
    dequantize(), and requantize().

    Latitude/longitude may be accessed via self-named attributes, self-
    named index keys, or 0/1. All comparison operators are supported.
    Inequalities use normal tuple comparison logic, so latitude is first
    compared and longitude is the tie-breaker.

    Latitude/longitude may be combined in a weighted fashion with either
    of two methods:
    - combine_locations() uses GeoLocations as a convenience, but note
      that successive calls will accumulate rounding errors.
    - combine_coordinates() uses Coordinates namedtuples of Decimals,
      so it is safe to use in successive calls.
    '''
    LATITUDE = 'latitude'
    LONGITUDE = 'longitude'
    COORDINATES = (LATITUDE, LONGITUDE)

    Coordinates = namedtuple('Coordinates', COORDINATES)

    @property
    def timezone(self):
        return pendulum.timezone(self.timezone_name)

    @property
    def timezone_name(self):
        tz_finder = TimezoneFinder()
        tz_name = tz_finder.timezone_at(lng=self.longitude, lat=self.latitude)
        if tz_name is None:
            tz_name = tz_finder.closest_timezone_at(lng=self.longitude,
                                                    lat=self.latitude)
        if tz_name is None:
            raise ValueError('No timezone exists for this geo location')
        return tz_name

    @property
    def latitude(self):
        '''Return latitude, a Coordinate'''
        return self._latitude

    @latitude.setter
    def latitude(self, value):
        '''Cast value to Coordinate and set as latitude'''
        self._latitude = Coordinate.cast(value)

    @property
    def longitude(self):
        '''Return longitude, a Coordinate'''
        return self._longitude

    @longitude.setter
    def longitude(self, value):
        '''Cast value to Coordinate and set as longitude'''
        self._longitude = Coordinate.cast(value)

    @property
    def coordinates(self):
        '''Return Coordinates namedtuple of latitude/longitude'''
        return self.Coordinates(self.latitude, self.longitude)

    @coordinates.setter
    def coordinates(self, values):
        '''Set latitude/longitude given an iterable of numbers'''
        self.latitude, self.longitude = values  # Invoke setters

    @property
    def values(self):
        '''Return Coordinates namedtuple of latitude/longitude values'''
        return self.Coordinates(self.latitude.value, self.longitude.value)

    def dequantize(self):
        '''Return Coordinates namedtuple of dequantized latitude/longitude'''
        return self.Coordinates(
            self.latitude.dequantize(), self.longitude.dequantize())

    @classmethod
    def requantize(cls, latitude, longitude):
        '''Return Coordinates namedtuple of requantized latitude/longitude'''
        return cls.Coordinates(
            Coordinate.requantize(latitude), Coordinate.requantize(longitude))

    @classmethod
    def combine_locations(cls, *weighted_locations):
        '''
        Combine locations and associated weights

        GeoLocations are accepted and returned as a convenience. Note
        that successive calls will accumulate rounding errors. Use
        combine_coordinates instead in such use cases.

        I/O:
        weighted_locations:
            Pairs of GeoLocations and weights, where weights are
            corresponding areas that can be cast to Decimals

        return: combined GeoLocation
        '''
        weighted_coordinates = (
            (geo_location.values, weight)
            for geo_location, weight in weighted_locations)

        return cls(*cls.combine_coordinates(*weighted_coordinates))

    @classmethod
    def combine_coordinates(cls, *weighted_coordinates):
        '''
        Combine (Decimal) coordinates and associated weights

        Tuples of Decimals are accepted and returned, so successive
        calls will NOT accumulate rounding errors.

        I/O:
        weighted_coordinates:
            Pairs of coordinates and weights, where coordinates are
            Decimal tuples representing latitude/longitude and weights
            are corresponding areas that can be cast to Decimals

        return: Coordinates namedtuple of combined latitude/longitude
        '''
        total_latitude = total_longitude = total_weight = 0

        for coordinate_values, weight in weighted_coordinates:
            raw_latitude, raw_longitude = coordinate_values
            latitude = QuantizedDecimal.cast_to_decimal(raw_latitude)
            longitude = QuantizedDecimal.cast_to_decimal(raw_longitude)
            weight = QuantizedDecimal.cast_to_decimal(weight)
            total_latitude += latitude * weight
            total_longitude += longitude * weight
            total_weight += weight

        total_latitude /= total_weight
        total_longitude /= total_weight
        return cls.Coordinates(total_latitude, total_longitude)

    @classmethod
    def cast(cls, value):
        '''Cast to GeoLocation, if not already one (i.e. if an iterable)'''
        return value if isinstance(value, cls) else cls(*value)

    def __init__(self, latitude, longitude, requantize=False):
        # Invoke setters upon assignment
        if not requantize:
            self.latitude, self.longitude = latitude, longitude
            return
        self.latitude, self.longitude = self.requantize(latitude, longitude)

    def __repr__(self):
        return "{cls}(latitude='{latitude}', longitude='{longitude}')".format(
            cls=self.__class__.__name__, **self.coordinates._asdict())

    def __str__(self):
        return str(self.coordinates)

    def jsonify(self, **json_kwargs):
        return self.Coordinates(str(self.latitude), str(self.longitude))

    # Container Methods

    def __getitem__(self, key):
        field = self.COORDINATES[key] if isinstance(key, INT_TYPES) else key
        if isinstance(field, basestring) and field[0] == '_':
            raise AttributeError('Attempting to access private member')
        return getattr(self, field)

    def __setitem__(self, key, value):
        field = self.COORDINATES[key] if isinstance(key, INT_TYPES) else key
        if isinstance(field, basestring) and field[0] == '_':
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

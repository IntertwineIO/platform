#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import pytest
import sys
from decimal import Decimal

from intertwine.utils.space import Area, Coordinate, GeoLocation

# Python version compatibilities
if sys.version_info >= (3,):
    long = int
    unicode = str


def perform_core_quantized_interactions(cls, number):
    """Test core interactions for QuantizedDecimal class"""
    precision = cls.DEFAULT_PRECISION
    multiplier = Decimal(10) ** precision
    decimal_value = Decimal(number)
    quantized_value = decimal_value.quantize(1 / multiplier)
    dequantized_value = int(quantized_value * multiplier)
    inst = cls(number)

    # Test properties and repr
    assert inst.precision == precision
    assert inst.value == quantized_value
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
def test_area_core_interactions(number):
    """Test core Area interactions"""
    perform_core_quantized_interactions(Area, number)


@pytest.mark.unit
@pytest.mark.parametrize('number', [
    str('0.1234567890'),
    float(12.1234567890),
    int(-90),
    long(90),
    0
])
def test_coordinate_core_interactions(number):
    """Test core Coordinate interactions"""
    perform_core_quantized_interactions(Coordinate, number)


@pytest.mark.unit
@pytest.mark.parametrize(('number1', 'number2'), [
    ('2.718281828', '3.14159265359'),
])
def test_geo_location_core_interactions(number1, number2):
    """Test core GeoLocation interactions"""
    coordinate1, coordinate2 = Coordinate(number1), Coordinate(number2)
    dequantized1 = coordinate1.dequantize()
    dequantized2 = coordinate2.dequantize()
    geo_location = GeoLocation(number1, number2)

    # Test str and repr
    geo_location_string = str(geo_location)
    assert str(coordinate1.value) in geo_location_string
    assert str(coordinate2.value) in geo_location_string
    assert eval(repr(geo_location)) == geo_location

    # Test indexes
    assert geo_location[GeoLocation.LATITUDE] == coordinate1
    assert geo_location[GeoLocation.LONGITUDE] == coordinate2
    assert geo_location[0] == coordinate1
    assert geo_location[1] == coordinate2

    # Test property getters
    assert geo_location.latitude == coordinate1
    assert geo_location.longitude == coordinate2
    assert geo_location.coordinates == (coordinate1, coordinate2)
    assert geo_location.values == (coordinate1.value, coordinate2.value)

    # Test property setters
    geo_location.latitude, geo_location.longitude = coordinate2, coordinate1
    assert geo_location.latitude is coordinate2
    assert geo_location.longitude is coordinate1
    geo_location.coordinates = (coordinate1, coordinate2)
    assert geo_location.coordinates == (coordinate1, coordinate2)

    # Test dequantize/requantize
    dequantized = geo_location.dequantize()
    assert dequantized == (dequantized1, dequantized2)
    assert GeoLocation.requantize(*dequantized) == geo_location.coordinates
    assert GeoLocation(*dequantized, requantize=True) == geo_location


@pytest.mark.unit
@pytest.mark.parametrize(
    ('lat1', 'lon1', 'wt1', 'lat2', 'lon2', 'wt2', 'lat3', 'lon3', 'wt3'),
    [('12.3456789', '12.3456789', '37.1234567',
      '-98.7654321', '98.7654321', '21.1234567',
      '-98.7654321', '-12.3456789', '42.1234567')])
def test_geo_location_combine(lat1, lon1, wt1, lat2, lon2, wt2, lat3, lon3, wt3):
    """Test GeoLocation combine methods"""
    geo_location1 = GeoLocation(lat1, lon1)
    geo_location2 = GeoLocation(lat2, lon2)
    geo_location3 = GeoLocation(lat3, lon3)

    lat_check = Coordinate((geo_location1.latitude * Decimal(wt1) +
                            geo_location2.latitude * Decimal(wt2) +
                            geo_location3.latitude * Decimal(wt3)) /
                           (Decimal(wt1) + Decimal(wt2) + Decimal(wt3)))
    lon_check = Coordinate((geo_location1.longitude * Decimal(wt1) +
                            geo_location2.longitude * Decimal(wt2) +
                            geo_location3.longitude * Decimal(wt3)) /
                           (Decimal(wt1) + Decimal(wt2) + Decimal(wt3)))

    coordinates_check = GeoLocation.Coordinates(lat_check, lon_check)

    # Combine GeoLocations
    combined_geo_locations = GeoLocation.combine_locations(
        (geo_location1, wt1), (geo_location2, wt2), (geo_location3, wt3))

    assert combined_geo_locations.coordinates == coordinates_check

    # Combine Coordinates
    combined_coordinates = GeoLocation.combine_coordinates(
        (geo_location1.coordinates, wt1),
        (geo_location2.coordinates, wt2),
        (geo_location3.coordinates, wt3))

    assert GeoLocation(*combined_coordinates) == coordinates_check

    # Combine Decimals
    combined_coordinate_values = GeoLocation.combine_coordinates(
        (geo_location1.values, wt1),
        (geo_location2.values, wt2),
        (geo_location3.values, wt3))

    assert GeoLocation(*combined_coordinate_values) == coordinates_check

    wt12 = Decimal(wt1) + Decimal(wt2)

    # Combine GeoLocations sequentially introduces rounding errors
    iterative_combined_geo_locations = GeoLocation.combine_locations(
        (geo_location1, wt1), (geo_location2, wt2))

    iterative_combined_geo_locations = GeoLocation.combine_locations(
        (iterative_combined_geo_locations, wt12), (geo_location3, wt3))

    assert iterative_combined_geo_locations != coordinates_check

    # Combine GeoLocations sequentially without rounding errors
    sequentially_combined_coordinates = GeoLocation.combine_coordinates(
        (geo_location1, wt1), (geo_location2, wt2))

    sequentially_combined_coordinates = GeoLocation.combine_coordinates(
        (sequentially_combined_coordinates, wt12), (geo_location3, wt3))

    assert GeoLocation(*sequentially_combined_coordinates) == coordinates_check

    # Combine Coordinates sequentially without rounding errors
    sequentially_combined_coordinates = GeoLocation.combine_coordinates(
        (geo_location1.coordinates, wt1), (geo_location2.coordinates, wt2))

    sequentially_combined_coordinates = GeoLocation.combine_coordinates(
        (sequentially_combined_coordinates, wt12),
        (geo_location3.coordinates, wt3))

    assert GeoLocation(*sequentially_combined_coordinates) == coordinates_check

    # Combine Decimals sequentially without rounding errors
    sequentially_combined_coordinates = GeoLocation.combine_coordinates(
        (geo_location1.values, wt1), (geo_location2.values, wt2))

    sequentially_combined_coordinates = GeoLocation.combine_coordinates(
        (sequentially_combined_coordinates, wt12),
        (geo_location3.values, wt3))

    assert GeoLocation(*sequentially_combined_coordinates) == coordinates_check

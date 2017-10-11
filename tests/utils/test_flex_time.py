#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import pytest
from datetime import datetime

from pendulum import Pendulum as DatetimeClass

from intertwine.utils.time import DatetimeInfo, FlexTime, UTC

datetime_tuples = [
    (2017, 8, 9, 0, 1, 23, 456789, UTC),
    (1990, 7, 8, 5, 6, 34, 129078, 'US/Central'),
    (1969, 2, 5, 8, 1, 47,  36925, 'US/Pacific')]


@pytest.mark.unit
@pytest.mark.parametrize(
    ('year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond',
        'tzinfo'), datetime_tuples)
@pytest.mark.parametrize('granularity', reversed(FlexTime.Granularity))
def test_flex_time_instantiation(
        session, year, month, day, hour, minute, second, microsecond, tzinfo,
        granularity):
    '''Test core interactions for FlexTime class'''
    full_dt_info = DatetimeInfo(
        year, month, day, hour, minute, second, microsecond, tzinfo)
    gval = granularity.value

    dt_info = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=False)
    dt_tuple = tuple(dt_info)
    dt_info_with_defaults = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=True)
    dt_info_with_defaults_and_tz_instance = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=True,
        tz_instance=True)

    native_dt = datetime(**dt_info_with_defaults_and_tz_instance._asdict())
    native_dt_via_args = datetime(*dt_info_with_defaults_and_tz_instance)
    assert native_dt == native_dt_via_args

    custom_dt = DatetimeClass(**dt_info_with_defaults._asdict())
    custom_dt_via_args = DatetimeClass(*dt_info_with_defaults)
    assert custom_dt == custom_dt_via_args
    assert native_dt == custom_dt

    flex_dt = FlexTime(**dt_info._asdict())
    flex_dt_via_args = FlexTime(tzinfo=dt_info.tzinfo, *dt_info[:gval])
    assert flex_dt == flex_dt_via_args
    assert flex_dt == native_dt
    assert flex_dt == custom_dt

    for dt in (dt_info, dt_tuple, native_dt, custom_dt, flex_dt):

        dt_info_null_backfill = FlexTime.form_info(
            dt, granularity=granularity, truncate=True, default=False)
        assert dt_info_null_backfill == dt_info

        dt_info_default_backfill = FlexTime.form_info(
            dt, granularity=granularity, truncate=True, default=True)
        assert dt_info_default_backfill == dt_info_with_defaults

        flex_dt_via_instance = FlexTime.instance(dt, granularity=granularity,
                                                 truncate=True)
        assert flex_dt_via_instance == flex_dt
        assert flex_dt_via_instance is not flex_dt


@pytest.mark.unit
@pytest.mark.parametrize(
    ('year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond',
        'tzinfo'), datetime_tuples)
@pytest.mark.parametrize('granularity', reversed(FlexTime.Granularity))
def test_core_flex_time_interactions(
        session, year, month, day, hour, minute, second, microsecond, tzinfo,
        granularity):
    '''Test core interactions for FlexTime class'''
    full_dt_info = DatetimeInfo(
        year, month, day, hour, minute, second, microsecond, tzinfo)
    gval = granularity.value

    dt_info = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=False)
    dt_info_with_defaults = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=True)
    dt_info_with_defaults_and_tz_instance = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=True,
        tz_instance=True)

    native_dt = datetime(**dt_info_with_defaults_and_tz_instance._asdict())
    custom_dt = DatetimeClass(**dt_info_with_defaults._asdict())
    flex_dt = FlexTime(*dt_info)

    assert flex_dt.info == dt_info
    assert flex_dt.deflex() == custom_dt

    flex_dt_via_copy = flex_dt.copy()
    assert flex_dt_via_copy is not flex_dt
    assert flex_dt_via_copy == flex_dt

    flex_dt_via_cast_native = FlexTime.cast(native_dt, granularity=granularity)
    assert flex_dt_via_cast_native == flex_dt
    assert flex_dt_via_cast_native is not flex_dt

    flex_dt_via_cast_custom = FlexTime.cast(custom_dt, granularity=granularity)
    assert flex_dt_via_cast_custom == flex_dt
    assert flex_dt_via_cast_custom is not flex_dt

    flex_dt_via_cast_flex = FlexTime.cast(flex_dt, granularity=granularity)
    assert flex_dt_via_cast_flex is flex_dt


@pytest.mark.unit
@pytest.mark.parametrize(
    ('year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond',
        'tzinfo'), datetime_tuples)
@pytest.mark.parametrize('granularity', reversed(FlexTime.Granularity))
def test_flex_time_zone_changes(
        session, year, month, day, hour, minute, second, microsecond, tzinfo,
        granularity):
    '''Test core interactions for FlexTime class'''
    full_dt_info = DatetimeInfo(
        year, month, day, hour, minute, second, microsecond, tzinfo)
    gval = granularity.value

    dt_info = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=False)
    flex_dt = FlexTime(*dt_info)
    dt_info_with_defaults = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=True)
    dt_custom = DatetimeClass(**dt_info_with_defaults._asdict())

    assert flex_dt == dt_custom

    flex_dt_utc = flex_dt.astimezone(UTC)
    custom_dt_utc = dt_custom.astimezone(UTC)

    assert flex_dt_utc == FlexTime.instance(custom_dt_utc)

    assert flex_dt == flex_dt_utc.astimezone(dt_info.tzinfo)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import pytest
import sys
from datetime import datetime

from pendulum import Pendulum as DatetimeClass

from intertwine.utils.time import DatetimeInfo, FlexTime, UTC

non_dst_datetime_tuples = [
    (2017, 8, 9, 0, 1, 23, 456789, UTC, 0),
    (1990, 7, 8, 5, 6, 34, 129078, 'US/Central', 0),
    (1969, 2, 5, 8, 1, 47,  36925, 'US/Pacific', 0)]

dst_datetime_tuples = [
    (2018, 3, 11, 2, 30, 0, 111111, 'US/Central', 0),
    (2018, 3, 11, 2, 30, 0, 111111, 'US/Central', 1),
    (2009, 11, 1, 1, 30, 0, 111111, 'US/Pacific', 0),
    (2009, 11, 1, 1, 30, 0, 111111, 'US/Pacific', 1)]


@pytest.mark.unit
@pytest.mark.parametrize('granularity', reversed(FlexTime.Granularity))
@pytest.mark.parametrize('tzinfo', (None, UTC, 'US/Central'))
def test_flex_time_now(
        session, tzinfo, granularity):
    '''Test now and utcnow for FlexTime class'''
    gval = granularity.value
    if granularity is FlexTime.MAX_GRANULARITY:
        base_now_before = DatetimeClass.now(tz=tzinfo)
        flex_now = FlexTime.now(tz=tzinfo, granularity=gval)
        base_now_after = DatetimeClass.now(tz=tzinfo)
        assert base_now_before < flex_now < base_now_after

        base_tz_name = FlexTime.tzinfo_name_cast(base_now_before.tzinfo)
        flex_tz_name = FlexTime.tzinfo_name_cast(flex_now.tzinfo)
        assert flex_tz_name == base_tz_name
    else:
        success_count = 0
        for i in range(2):
            base_now = DatetimeClass.now(tz=tzinfo)
            flex_now = FlexTime.now(tz=tzinfo, granularity=gval)
            # If they span a second change, next time they will not
            if FlexTime.cast(base_now, granularity=gval) == flex_now:
                success_count += 1

        assert success_count > 0


@pytest.mark.unit
@pytest.mark.parametrize('granularity', reversed(FlexTime.Granularity))
@pytest.mark.parametrize(
    ('year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond',
        'tzinfo', 'fold'), non_dst_datetime_tuples)
def test_flex_time_instantiation(
        session, year, month, day, hour, minute, second, microsecond, tzinfo,
        fold, granularity):
    '''Test core instantiation methods for FlexTime class'''
    full_dt_info = DatetimeInfo(
        year, month, day, hour, minute, second, microsecond, tzinfo, fold)
    gval = granularity.value

    dt_info = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=False)
    dt_tuple = tuple(dt_info)
    dt_info_with_defaults = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=True)
    dt_info_native = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=True,
        tz_instance=True)

    dt_native_kwargs = dt_info_native._asdict()
    if sys.version_info < (3, 6):
        del dt_native_kwargs[FlexTime.FOLD_TAG]
    native_dt = datetime(**dt_native_kwargs)

    dt_native_args = dt_info_native[:FlexTime.FOLD_IDX]
    if sys.version_info < (3, 6):
        native_dt_via_args = datetime(*dt_native_args)
    else:
        native_dt_via_args = datetime(fold=fold, *dt_native_args)
    assert native_dt == native_dt_via_args

    dt_naive_kwargs = dt_info_native._asdict()
    if sys.version_info < (3, 6):
        del dt_naive_kwargs[FlexTime.FOLD_TAG]
    del dt_naive_kwargs[FlexTime.TZINFO_TAG]
    naive_dt = datetime(**dt_naive_kwargs)

    dt_naive_args = dt_info_native[:FlexTime.TZINFO_IDX]
    if sys.version_info < (3, 6):
        naive_dt_via_args = datetime(*dt_naive_args)
    else:
        naive_dt_via_args = datetime(fold=fold, *dt_naive_args)
    assert naive_dt == naive_dt_via_args

    base_dt = DatetimeClass(**dt_info_with_defaults._asdict())
    base_dt_via_args = DatetimeClass(*dt_info_with_defaults)
    assert base_dt == base_dt_via_args
    assert native_dt == base_dt

    flex_dt = FlexTime(**dt_info._asdict())
    flex_dt_via_args = FlexTime(tzinfo=dt_info.tzinfo, *dt_info[:gval])
    assert flex_dt == flex_dt_via_args
    assert flex_dt == base_dt
    assert flex_dt == native_dt  # True only if not in DST

    for dt in (dt_info, dt_tuple, native_dt, naive_dt, base_dt, flex_dt,
               flex_dt.info):

        tz = dt_info.tzinfo if dt is naive_dt else None

        dt_info_null_backfill = FlexTime.form_info(
            dt, tz=tz, granularity=granularity, truncate=True, default=False)
        assert dt_info_null_backfill == dt_info

        dt_info_default_backfill = FlexTime.form_info(
            dt, tz=tz, granularity=granularity, truncate=True, default=True)
        assert dt_info_default_backfill == dt_info_with_defaults

        flex_dt_via_instance = FlexTime.instance(dt, tz=tz,
                                                 granularity=granularity)
        assert flex_dt_via_instance == flex_dt
        assert flex_dt_via_instance is not flex_dt
        assert flex_dt_via_instance.info == dt_info  # True only if not in DST


@pytest.mark.unit
@pytest.mark.parametrize('granularity', reversed(FlexTime.Granularity))
@pytest.mark.parametrize(
    ('year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond',
        'tzinfo', 'fold'), non_dst_datetime_tuples)
def test_core_flex_time_interactions(
        session, year, month, day, hour, minute, second, microsecond, tzinfo,
        fold, granularity):
    '''Test core interactions for FlexTime class'''
    full_dt_info = DatetimeInfo(
        year, month, day, hour, minute, second, microsecond, tzinfo, fold)
    gval = granularity.value

    dt_info = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=False)
    dt_info_with_defaults = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=True)
    dt_info_native = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=True,
        tz_instance=True)

    dt_native_kwargs = dt_info_native._asdict()
    if sys.version_info < (3, 6):
        del dt_native_kwargs[FlexTime.FOLD_TAG]

    native_dt = datetime(**dt_native_kwargs)
    base_dt = DatetimeClass(**dt_info_with_defaults._asdict())
    flex_dt = FlexTime(*dt_info)

    assert flex_dt.info == dt_info
    assert flex_dt.deflex() == base_dt
    assert flex_dt.deflex(native=True) == native_dt

    flex_dt_via_copy = flex_dt.copy()
    assert flex_dt_via_copy is not flex_dt
    assert flex_dt_via_copy == flex_dt

    flex_dt_via_cast_native = FlexTime.cast(native_dt, granularity=granularity)
    assert flex_dt_via_cast_native == flex_dt
    assert flex_dt_via_cast_native is not flex_dt

    flex_dt_via_cast_base = FlexTime.cast(base_dt, granularity=granularity)
    assert flex_dt_via_cast_base == flex_dt
    assert flex_dt_via_cast_base is not flex_dt

    flex_dt_via_cast_flex = FlexTime.cast(flex_dt, granularity=granularity)
    assert flex_dt_via_cast_flex is flex_dt


@pytest.mark.unit
@pytest.mark.parametrize('granularity', reversed(FlexTime.Granularity))
@pytest.mark.parametrize(
    ('year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond',
        'tzinfo', 'fold'), dst_datetime_tuples)
def test_flex_time_zone_changes(
        session, year, month, day, hour, minute, second, microsecond, tzinfo,
        fold, granularity):
    '''Test time zone changes for FlexTime class'''
    full_dt_info = DatetimeInfo(
        year, month, day, hour, minute, second, microsecond, tzinfo, fold)
    gval = granularity.value

    dt_info = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=False)
    flex_dt = FlexTime(*dt_info)

    dt_info_with_defaults = FlexTime.form_info(
        full_dt_info, granularity=gval, truncate=True, default=True)
    base_dt = DatetimeClass(**dt_info_with_defaults._asdict())

    assert flex_dt == base_dt

    flex_dt_utc = flex_dt.astimezone(UTC)
    base_dt_utc = base_dt.astimezone(UTC)
    assert flex_dt_utc == base_dt_utc

    # Pendulum.instance does not handle fold properly
    # assert flex_dt_utc == FlexTime.instance(base_dt_utc, granularity=gval)

    flex_dt_there_and_back_again = flex_dt_utc.astimezone(dt_info.tzinfo)
    base_dt_there_and_back_again = base_dt_utc.astimezone(dt_info.tzinfo)
    assert flex_dt_there_and_back_again == base_dt_there_and_back_again

    assert flex_dt_there_and_back_again == flex_dt

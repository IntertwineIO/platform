#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import pytest
from datetime import datetime

from pendulum import Pendulum as DatetimeClass
from pendulum import timezone

from intertwine.utils.time import DatetimeInfo, FlexTime, UTC


@pytest.mark.unit
@pytest.mark.parametrize(
    ('year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond',
        'tzinfo'),
    [(2012, 3, 4, 5,  6,  7, 890123, 'US/Pacific'),
     (1999, 8, 7, 6, 54, 32, 109876, 'US/Central')])
def test_core_flex_time_interactions(
    session, year, month, day, hour, minute, second, microsecond, tzinfo):
    '''Test core interactions for FlexTime class'''
    dt_info = DatetimeInfo(
        year, month, day, hour, minute, second, microsecond, tzinfo)

    for gval in range(FlexTime.MAX_GRANULARITY.value, 0, -1):
        dt_info = FlexTime.create_datetime_info(
            dt_info, granularity=gval, default=False)
        dt_info_with_defaults = FlexTime.create_datetime_info(
            dt_info, granularity=gval, default=True)
        dt_info_with_defaults_and_tz_instance = FlexTime.create_datetime_info(
            dt_info, granularity=gval, default=True, tz_instance=True)
        dt_check = DatetimeClass(**dt_info_with_defaults._asdict())
        dt_check2 = datetime(**dt_info_with_defaults_and_tz_instance._asdict())

        assert dt_check2 == dt_check

        flex_dt = FlexTime.instance(dt_info)

        assert FlexTime.create_datetime_info(flex_dt) == dt_info
        assert FlexTime.create_datetime_info(dt_check, gval) == dt_info
        assert FlexTime.create_datetime_info(dt_check2, gval) == dt_info

        flex_dt_via_cast = FlexTime.cast(dt_check, granularity=gval)
        flex_dt_via_instance = FlexTime.instance(dt_check, granularity=gval)
        flex_dt_via_args = FlexTime(tzinfo=dt_info[-1], *dt_info[:gval])
        flex_dt_via_kwargs = FlexTime(**dt_info._asdict())

        assert FlexTime.cast(flex_dt) is flex_dt
        assert flex_dt_via_cast is not flex_dt

        assert flex_dt == dt_check
        assert flex_dt_via_cast == dt_check
        assert flex_dt_via_instance == dt_check
        assert flex_dt_via_args == dt_check
        assert flex_dt_via_kwargs == dt_check

        assert flex_dt.granularity.value == gval
        assert flex_dt_via_cast.granularity.value == gval
        assert flex_dt_via_instance.granularity.value == gval
        assert flex_dt_via_args.granularity.value == gval
        assert flex_dt_via_kwargs.granularity.value == gval

        assert flex_dt.datetime_info == dt_info
        assert flex_dt_via_cast.datetime_info == dt_info
        assert flex_dt_via_instance.datetime_info == dt_info
        assert flex_dt_via_args.datetime_info == dt_info
        assert flex_dt_via_kwargs.datetime_info == dt_info

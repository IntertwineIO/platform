#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime
import sys
from collections import namedtuple
from enum import Enum
from itertools import chain, islice

from pendulum import DateTime, timezone


UTC = 'UTC'
TZ_UTC = timezone(UTC)

DateTimeInfo = namedtuple(
    'DateTimeInfo',
    'year, month, day, hour, minute, second, microsecond, tzinfo, fold')

PendulumInfo = namedtuple(
    'PendulumInfo',
    'year, month, day, hour, minute, second, microsecond, tz, dst_rule')

# TODO: obtain timezone based on geo


class FlexTime(DateTime):
    """
    FlexTime

    A datetime supporting varying degrees of granularity in the time
    unit components, ranging from year to microsecond. A flextime
    instance is a datetime with granularity and info members:

    - granularity is an enum of DateTimeInfo fields excluding tzinfo
    - info is a DateTimeInfo tuple in which unspecified units are None
    - the underlying datetime representation defaults unspecified units

    Upon creation via init(), granularity is determined based on the
    specified units and info contains None beyond this granularity.

    However, creation via instance() permits the granularity to differ
    from what would be implied by the specified units. This is necessary
    to support timezone changes. Specifically, the granularity remains
    constant through timezone changes, even if such changes require
    specifying units beyond the granularity.

    Alignment between granularity and the underlying datetime instance
    can be enforced via an optional 'truncate' parameter.
    """
    TZINFO_TAG = 'tzinfo'
    TZINFO_IDX = DateTimeInfo._fields.index(TZINFO_TAG)
    FOLD_TAG = 'fold'
    FOLD_IDX = DateTimeInfo._fields.index(FOLD_TAG)
    LOCAL_TAG = 'local'
    Granularity = Enum('Granularity',
                       [f.upper() for f in DateTimeInfo._fields[:TZINFO_IDX]])
    MAX_GRANULARITY = Granularity(len(Granularity))
    DEFAULTS = DateTimeInfo(None, 1, 1, 0, 0, 0, 0, UTC, 0)
    NULLS = DateTimeInfo(*(None for _ in range(len(DateTimeInfo._fields))))

    @classmethod
    def determine_granularity(cls, dt, granularity=None, extend=False):
        """
        Determine granularity

        If a granularity is provided, use it.
        If dt has a granularity member variable, use it.
        If dt is a datetime instance, use MAX GRANULARITY.
        If dt is a DateTimeInfo namedtuple or tuple, derive granularity,
            and validate there are no gaps.
        If extend is True, the granularity is increased to represent the
        given datetime without data loss. This means all units past the
        granularity are either null or defaults.

        I/O:
        dt: a flextime, datetime, dtinfo namedtuple or plain tuple
        granularity=None: a granularity or its integer value
        extend=False: if True, granularity is extended per above
        return: granularity enum instance
        """
        gmax = cls.MAX_GRANULARITY.value

        for single_loop_to_enable_exception_flow_control in range(1):

            if granularity is not None:
                gval = cls.Granularity(granularity).value
                continue  # execution proceeds after single loop

            try:
                gval = dt.granularity.value  # AttributeError if not flex dt
                continue  # execution proceeds after single loop
            except AttributeError:
                pass

            try:
                dt_units = islice(dt, gmax)  # TypeError if dt
            except TypeError:
                gval = gmax
            else:
                has_value_tuple = tuple(t is not None for t in dt_units)
                gval = sum(has_value_tuple)
                check_sum = sum(has_value_tuple[:gval])
                if check_sum < gval:
                    raise ValueError(
                        'Gap in datetime info tuple: {}'.format(dt))

        # after single loop: execution proceeds here
        if extend:
            for i in range(gmax, gval, -1):
                index = i - 1
                value = cls.extract_field(dt, idx=index)
                if value is not None and value != cls.DEFAULTS[index]:
                    gval = i
                    break

        return cls.Granularity(gval)

    def derive_info(self, granularity=None, truncate=False, default=False,
                    tz_instance=False):
        """Derive dtinfo from flextime instance"""
        return self.form_info(self, granularity=granularity, truncate=truncate,
                              default=default, tz_instance=tz_instance)

    @classmethod
    def form_info(cls, dt, tz=None, granularity=None, truncate=False,
                  default=False, tz_instance=False):
        """
        Form (datetime) info

        I/O:
        dt: a flextime, datetime, dtinfo namedtuple or plain tuple
        tz=None: a timezone instance or name in case dt has no timezone
        granularity=None: a granularity or its integer value; if not
            provided, it is determined from the dt parameter
        truncate=False: if True, replace all units past granularity with
            None/default, based on 'default' parameter; if False, keep
            non-null units past granularity that differ from default
        default=False: if True, default units beyond granularity;
            if False, nullify units beyond granularity
        tz_instance=False: if True, cast to tzinfo instance; if False,
            cast to timezone name
        return: DateTimeInfo namedtuple
        """
        granularity = cls.determine_granularity(dt, granularity,
                                                extend=not truncate)
        gval, gmax = granularity.value, cls.MAX_GRANULARITY.value
        fields = DateTimeInfo._fields
        backfill_source = cls.DEFAULTS if default else cls.NULLS

        granular = (cls.extract_field(dt, idx=i)
                    for i, f in enumerate(fields[:gval]))
        backfill = (backfill_source[i]
                    for i, f in enumerate(fields[gval:gmax], start=gval))
        other = (cls.extract_tzinfo(dt, tz_instance, default=tz),
                 cls.extract_field(dt, field=cls.FOLD_TAG))

        return DateTimeInfo(*chain(granular, backfill, other))

    @classmethod
    def extract_field(cls, dt, idx=None, field=None):
        """Extract field from datetime or tuple given field or idx"""
        field = field or DateTimeInfo._fields[idx]
        try:
            return getattr(dt, field)  # raise if plain tuple or fold < py3.6
        except AttributeError:
            pass
        idx = idx if idx is not None else DateTimeInfo._fields.index(field)
        try:
            return dt[idx]  # raise on datetime.fold if < py3.6
        except TypeError:  # ...datetime object has no attribute '__getitem__'
            return cls.DEFAULTS[idx]

    @classmethod
    def extract_tzinfo(cls, dt, tz_instance=False, default=None):
        """Extract tzinfo name or instance from dt instance or tuple"""
        try:
            tzinfo = dt.tzinfo
        except AttributeError:
            tzinfo = dt[cls.TZINFO_IDX]
        return (cls.timezone(tzinfo, default) if tz_instance
                else cls.timezone_name(tzinfo, default))

    @classmethod
    def timezone(cls, tz, default=None):
        """Get timezone instance from tzinfo string or instance"""
        tz = tz or default or cls.DEFAULTS.tzinfo
        if isinstance(tz, datetime.tzinfo):
            return tz
        return timezone(tz)

    @classmethod
    def timezone_name(cls, tz, default=None):
        """Get timezone name from tzinfo string or instance"""
        default = (cls.DEFAULTS.tzinfo if default is None else
                   cls.timezone_name(tz=default))
        try:
            return tz.name or default  # pendulum
        except AttributeError:
            # tzinfo is None, pytz instance, or tzinfo string
            return default if tz is None else str(tz)

    def deflex(self, native=False):
        """Deflex instance by creating copy with parent DateTime"""
        dt_info = self.form_info(self, granularity=self.MAX_GRANULARITY,
                                 default=True, tz_instance=True)
        dt_kwds = dt_info._asdict()
        if native and sys.version_info < (3, 6):
            del dt_kwds[self.FOLD_TAG]
        return (datetime.datetime(**dt_kwds) if native
                else DateTime(**dt_kwds))

    @classmethod
    def now(cls, tz=None, granularity=None):
        """Now returns current time (default local) with given granularity"""
        tz = tz or cls.LOCAL_TAG  # default to local, not UTC
        return cls.cast(super(FlexTime, cls).now(tz), granularity=granularity)

    def astimezone(self, tz, **kwds):
        """Astimezone converts flextime instance to the given time zone"""
        dt = super(FlexTime, self).astimezone(self.timezone(tz), **kwds)
        return self.instance(dt, granularity=self.granularity, truncate=False)

    def copy(self, **kwds):
        """Copy flextime instance"""
        return self.instance(self, granularity=self.granularity, truncate=False)

    @classmethod
    def cast(cls, dt, tz=None, granularity=None):
        """Cast datetime or dtinfo to flextime at given granularity"""
        if (isinstance(dt, FlexTime) and (
                not granularity or dt.granularity == cls.Granularity(granularity))):
            return dt
        return cls.instance(dt, tz=tz, granularity=granularity, truncate=True)

    @classmethod
    def instance(cls, dt, tz=None, granularity=None, truncate=False, **kwds):
        """
        Instance

        I/O:
        dt:                 flextime, datetime, dtinfo, or plain tuple
        tz=None:            timezone or name in case dt has no timezone
        granularity=None:   granularity enum or its integer value
        truncate=False:     if True, values past granularity are removed
        return:             new flextime instance with granularity/info
        """
        granularity = cls.determine_granularity(dt, granularity)

        dt_info = cls.form_info(dt, tz=tz, granularity=granularity,
                                truncate=truncate, default=False,
                                tz_instance=True)
        inst = cls(granularity=granularity, **dt_info._asdict())
        return inst

    def __new__(cls, year=None, month=None, day=None,
                hour=None, minute=None, second=None, microsecond=None,
                tzinfo=None, fold=None, granularity=None, **kwds):
        fold = cls.DEFAULTS.fold if fold is None else fold
        dt_info = DateTimeInfo(
            year, month, day, hour, minute, second, microsecond, tzinfo, fold)
        granularity = cls.determine_granularity(dt_info, granularity)
        super_kwds = cls.form_info(dt_info, granularity=granularity,
                                   default=True, tz_instance=True)._asdict()
        super_kwds.update(kwds)
        inst = super(FlexTime, cls).__new__(cls, **super_kwds)
        inst.granularity = granularity
        # set info with a tz name, not a tzinfo instance
        inst.info = cls.form_info(dt_info, granularity=granularity)
        return inst

    def __repr__(self):
        gmax = self.MAX_GRANULARITY.value
        return ("{cls}({args}, tzinfo='{tzinfo}', fold={fold}, "
                "granularity={granularity})"
                .format(cls=self.__class__.__name__,
                        args=', '.join(str(t) for t in islice(self.info, gmax)
                                       if t is not None),
                        tzinfo=self.tzinfo.name, fold=self.fold,
                        granularity=self.granularity.value))

    def __eq__(self, other):
        try:
            # info is not compared to support equality across time zones
            return (self.granularity is other.granularity and super(FlexTime, self).__eq__(other))
        except AttributeError:
            return super(FlexTime, self).__eq__(other)

    def __ne__(self, other):
        return not (self == other)

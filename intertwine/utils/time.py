#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime
import sys
from collections import namedtuple
from enum import Enum
from itertools import chain, islice

from pendulum import Pendulum as DatetimeClass
from pendulum import timezone


UTC = 'UTC'
TZ_UTC = timezone(UTC)

# fold not yet supported as Pendulum uses a non-standard default of 1
DatetimeInfo = namedtuple(
    'DatetimeInfo',
    'year, month, day, hour, minute, second, microsecond, tzinfo, fold')


# TODO: obtain timezone based on geo


class FlexTime(DatetimeClass):
    '''
    FlexTime

    A datetime supporting varying degrees of granularity in the time
    unit components, ranging from year to microsecond. A flextime
    instance is a datetime with granularity and info members:

    - granularity is an enum of DatetimeInfo fields excluding tzinfo
    - info is a DatetimeInfo tuple in which unspecified units are None
    - the underlying datetime representation defaults unspecified units

    Upon creation via init(), the granularity is determined based on the
    unspecified units and info contains None beyond this granularity.

    However, creation via instance() permits the granularity to differ
    from what would be implied by the unspecified units. This is
    necessary to support timezone changes. Specifically, the granularity
    remains constant through timezone changes, even if such changes
    require specifying units beyond the granularity.

    Alignment between granularity and the underlying datetime instance
    can be enforced via an optional 'truncate' parameter.
    '''
    TZINFO_TAG = 'tzinfo'
    TZINFO_IDX = DatetimeInfo._fields.index(TZINFO_TAG)
    FOLD_TAG = 'fold'
    FOLD_IDX = DatetimeInfo._fields.index(FOLD_TAG)
    LOCAL_TAG = 'local'
    Granularity = Enum('Granularity',
                       [f.upper() for f in DatetimeInfo._fields[:TZINFO_IDX]])
    MAX_GRANULARITY = tuple(Granularity)[-1]
    DEFAULTS = DatetimeInfo(None, 1, 1, 0, 0, 0, 0, UTC, 0)
    NULLS = DatetimeInfo(*(None for _ in range(len(DatetimeInfo._fields))))

    @classmethod
    def determine_granularity(cls, dt, granularity=None, extend=False):
        '''
        Determine granularity

        If a granularity is provided, use it.
        If dt has a granularity member variable, use it.
        If dt is a datetime instance, use MAX GRANULARITY.
        If dt is a DatetimeInfo namedtuple or tuple, derive granularity,
            and validate there are no gaps.
        If extend is True, the granularity is increased to represent the
        given datetime without data loss. This means all units past the
        granularity are either null or defaults.

        I/O:
        dt: a flextime, datetime, dtinfo namedtuple or plain tuple
        granularity=None: a granularity or its integer value
        extend=False: if True, granularity is extended per above
        return: granularity enum instance
        '''
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
                # create datetime info generator excluding tzinfo/fold
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
            for i in range(gmax - 1, gval - 1, -1):
                value = cls.extract_field(dt, idx=i)
                if value is not None and value != cls.DEFAULTS[i]:
                    gval = i + 1
                    break

        return cls.Granularity(gval)

    def derive_info(self, granularity=None, truncate=False, default=False,
                    tz_instance=False):
        '''Derive dtinfo from flextime instance'''
        return self.form_info(self, granularity=granularity, truncate=truncate,
                              default=default, tz_instance=tz_instance)

    @classmethod
    def form_info(cls, dt, tz=None, granularity=None, truncate=False,
                  default=False, tz_instance=False):
        '''
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
        return: DatetimeInfo namedtuple
        '''
        granularity = cls.determine_granularity(dt, granularity,
                                                extend=not truncate)
        gval, gmax = granularity.value, cls.MAX_GRANULARITY.value
        fields = DatetimeInfo._fields
        backfill_source = cls.DEFAULTS if default else cls.NULLS

        granular = (cls.extract_field(dt, idx=i)
                    for i, f in enumerate(fields[:gval]))
        backfill = (backfill_source[i]
                    for i, f in enumerate(fields[gval:gmax], start=gval))
        other = (cls.extract_tzinfo(dt, tz_instance, default=tz),
                 cls.extract_field(dt, field=cls.FOLD_TAG))

        return DatetimeInfo(*chain(granular, backfill, other))

    @classmethod
    def extract_field(cls, dt, idx=None, field=None):
        '''Extract field from datetime or tuple given field or idx'''
        field = field or DatetimeInfo._fields[idx]
        try:
            return getattr(dt, field)  # raise if plain tuple or fold < py3.6
        except AttributeError:
            pass
        idx = idx if idx is not None else DatetimeInfo._fields.index(field)
        try:
            return dt[idx]  # raise on datetime.fold if < py3.6
        except TypeError:  # ...datetime object has no attribute '__getitem__'
            return cls.DEFAULTS[idx]

    @classmethod
    def extract_tzinfo(cls, dt, tz_instance=False, default=None):
        '''Extract tzinfo name or instance from dt instance or tuple'''
        try:
            tzinfo = dt.tzinfo
        except AttributeError:
            tzinfo = dt[cls.TZINFO_IDX]
        return cls.tzinfo_cast(tzinfo, tz_instance, default)

    @classmethod
    def tzinfo_cast(cls, tzinfo, tz_instance=False, default=None):
        '''Cast tzinfo name or instance to tzinfo name or instance'''
        return (cls.tzinfo_instance_cast(tzinfo, default) if tz_instance
                else cls.tzinfo_name_cast(tzinfo, default))

    @classmethod
    def tzinfo_instance_cast(cls, tzinfo, default=None):
        '''Get timezone instance from tzinfo string or instance'''
        tzinfo = tzinfo or default or cls.DEFAULTS.tzinfo
        try:
            return timezone(tzinfo)  # AttributeError if tzinfo instance
        except (AttributeError, TypeError, ValueError):
            return tzinfo

    @classmethod
    def tzinfo_name_cast(cls, tzinfo, default=None):
        '''Get timezone name from tzinfo string or instance'''
        default = (cls.DEFAULTS.tzinfo if default is None else
                   cls.tzinfo_name_cast(tzinfo=default))
        try:
            return tzinfo.name or default  # pendulum
        except AttributeError:
            # tzinfo is None, pytz instance, or tzinfo string
            return default if tzinfo is None else str(tzinfo)

    def deflex(self, native=False):
        '''Deflex instance by creating copy with parent DatetimeClass'''
        if not native:
            try:
                # Raise if super has no instance method
                return super(FlexTime, self).instance(self)
            except AttributeError:
                pass
        dt_info = self.form_info(self, granularity=self.MAX_GRANULARITY,
                                 default=True, tz_instance=True)
        dt_kwds = dt_info._asdict()
        if native and sys.version_info < (3, 6):
            del dt_kwds[self.FOLD_TAG]
        return (datetime.datetime(**dt_kwds) if native
                else DatetimeClass(**dt_kwds))

    @classmethod
    def now(cls, tz=None, granularity=None):
        '''Now returns current time (default local) with given granularity'''
        tz = tz or cls.LOCAL_TAG
        # Now defaults to local explicitly since instance defaults to UTC
        return cls.cast(super(FlexTime, cls).now(tz), granularity=granularity)

    @classmethod
    def utcnow(cls, granularity=None):
        '''UTC now returns current UTC time with given granularity'''
        return cls.cast(super(FlexTime, cls).utcnow(), granularity=granularity)

    def astimezone(self, tz, **kwds):
        '''Astimezone converts flextime instance to the given time zone'''
        super_astimezone = super(FlexTime, self).astimezone
        try:
            # raise TypeError if DatetimeClass requires tzinfo (e.g. datetime)
            dt = super_astimezone(tz, **kwds)
        except TypeError:  # ...argument 1 must be datetime.tzinfo, not unicode
            dt = super_astimezone(self.tzinfo_instance_cast(tz), **kwds)

        dt.granularity = self.granularity
        dt.info = self.form_info(dt, granularity=self.granularity,
                                 truncate=False, default=False)
        return dt

    def copy(self, **kwds):
        '''Copy flextime instance'''
        try:
            # raise if super has no copy()
            dt = super(FlexTime, self).copy(**kwds)
            dt.granularity = self.granularity
            dt.info = self.info
        except AttributeError:
            dt = self.instance(self, granularity=self.granularity,
                               truncate=False)
        return dt

    @classmethod
    def cast(cls, dt, tz=None, granularity=None):
        '''Cast datetime or dtinfo to flextime at given granularity'''
        if (isinstance(dt, FlexTime) and (
                not granularity or
                dt.granularity == cls.Granularity(granularity))):
            return dt
        return cls.instance(dt, tz=tz, granularity=granularity, truncate=True)

    @classmethod
    def instance(cls, dt, tz=None, granularity=None, truncate=False, **kwds):
        '''
        Instance

        I/O:
        dt: a flextime, datetime, dtinfo namedtuple or plain tuple
        granularity=None: a granularity or the integer value
        truncate=False: if True, values past granularity are removed
        return: new datetime instance with granularity and datetime info
        '''
        granularity = cls.determine_granularity(dt, granularity)

        # Do NOT call super().instance since it fails to handle fold
        dt_info = cls.form_info(dt, tz=tz, granularity=granularity,
                                truncate=truncate, default=False,
                                tz_instance=True)
        return cls(**dt_info._asdict())

    def __new__(cls, year=None, month=None, day=None,
                hour=None, minute=None, second=None, microsecond=None,
                tzinfo=None, fold=None, **kwds):
        fold = cls.DEFAULTS.fold if fold is None else fold
        dt_info = DatetimeInfo(
            year, month, day, hour, minute, second, microsecond, tzinfo, fold)
        granularity = cls.determine_granularity(dt_info)
        super_kwds = cls.form_info(dt_info, granularity=granularity,
                                   default=True, tz_instance=True)._asdict()
        super_kwds.update(kwds)
        inst = super(FlexTime, cls).__new__(cls, **super_kwds)
        inst.granularity = granularity
        inst.info = dt_info
        return inst

    def __init__(self, year=None, month=None, day=None,
                 hour=None, minute=None, second=None, microsecond=None,
                 tzinfo=None, fold=None, **kwds):
        super_kwds = self.form_info(self.info, granularity=self.granularity,
                                    default=True, tz_instance=True)._asdict()
        super_kwds.update(kwds)
        super(FlexTime, self).__init__(**super_kwds)
        self.info = self.form_info(self, granularity=self.granularity)

    def __repr__(self):
        return ('{cls}.instance({info}, granularity={granularity})'
                .format(cls=self.__class__.__name__, info=self.info,
                        granularity=self.granularity.value))

    # Comparison Operators

    def __eq__(self, other):
        try:
            # info is not compared to support equality across time zones
            return (self.granularity is other.granularity and
                    super(FlexTime, self).__eq__(other))
        except AttributeError:
            return super(FlexTime, self).__eq__(other)

    def __ne__(self, other):
        return not (self == other)

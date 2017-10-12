#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from collections import namedtuple
from enum import Enum
from itertools import chain, islice

from pendulum import Pendulum as DatetimeClass
from pendulum import timezone


UTC = 'UTC'

DatetimeInfo = namedtuple(
    'DatetimeInfo',
    'year, month, day, hour, minute, second, microsecond, tzinfo')


# TODO: obtain timezone based on geo


class FlexTime(DatetimeClass):
    '''
    FlexTime

    A datetime constructor to enable varying degrees of granularity
    based on the time unit components, ranging from year to microsecond.
    Each instance is a datetime that has been truncated to the specified
    granularity by substituting default values. Each instance keeps
    track of its granularity and datetime info tuple.
    '''
    TZINFO_TAG = 'tzinfo'
    TZINFO_IDX = DatetimeInfo._fields.index(TZINFO_TAG)
    Granularity = Enum('Granularity', DatetimeInfo._fields[:TZINFO_IDX])
    MAX_GRANULARITY = tuple(Granularity)[-1]
    DEFAULTS = DatetimeInfo(None, 1, 1, 0, 0, 0, 0, UTC)
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
                continue  # Execution proceeds after single loop

            try:
                gval = dt.granularity.value  # AttributeError if not flex dt
                continue  # Execution proceeds after single loop
            except AttributeError:
                pass

            try:
                # Create dt list without tzinfo
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

        # After single loop: execution proceeds here
        if extend:
            for i in range(gmax - 1, gval - 2, -1):
                value = cls.extract_field(dt, idx=i)
                if value is not None and value != cls.DEFAULTS[i]:
                    break
            gval = i + 1

        return cls.Granularity(gval)

    def derive_info(self, granularity=None, truncate=False, default=False,
                    tz_instance=False):
        '''Derive dtinfo from flextime instance'''
        return self.form_info(self, granularity=granularity, truncate=truncate,
                              default=default, tz_instance=tz_instance)

    @classmethod
    def form_info(cls, dt, granularity=None, truncate=False, default=False,
                  tz_instance=False):
        '''
        Form datetime info

        I/O:
        dt: a flextime, datetime, dtinfo namedtuple or plain tuple
        granularity=None: a granularity or its integer value; if not
            provided, it is determined from the dt parameter
        truncate=False: if True, replace all units past granularity with
            None/default, based on 'default' parameter; if False, keep
            non-null units past granularity that differ from default
        default=False: if True, default units beyond granularity;
            if False, nullify units beyond granularity
        return: DatetimeInfo instance (namedtuple)
        '''
        granularity = cls.determine_granularity(dt, granularity,
                                                extend=not truncate)
        gval, gmax = granularity.value, cls.MAX_GRANULARITY.value
        fields = DatetimeInfo._fields
        backfill = cls.DEFAULTS if default else cls.NULLS

        granular = (cls.extract_field(dt, idx=i)
                    for i, f in enumerate(fields[:gval]))
        remainder = (backfill[i]
                     for i, f in enumerate(fields[gval:gmax], start=gval))
        tzinfo = (cls.extract_tzinfo(dt, tz_instance),)

        return DatetimeInfo(*chain(granular, remainder, tzinfo))

    @classmethod
    def extract_field(cls, dt, idx=None, field=None):
        '''Extract field from datetime or tuple given field or idx'''
        field = field or DatetimeInfo._fields[idx]
        try:
            return getattr(dt, field)  # raise if plain tuple
        except AttributeError:
            return dt[idx]

    @classmethod
    def extract_tzinfo(cls, dt, tz_instance=False):
        '''Extract tzinfo name or instance from dt instance or tuple'''
        try:
            tzinfo = dt.tzinfo
        except AttributeError:
            tzinfo = dt[cls.TZINFO_IDX]
        return cls.tzinfo_cast(tzinfo, tz_instance)

    @classmethod
    def tzinfo_cast(cls, tzinfo, tz_instance=None):
        '''Cast tzinfo name or instance to tzinfo name or instance'''
        return (cls.get_tzinfo_instance(tzinfo) if tz_instance
                else cls.get_tzinfo_name(tzinfo))

    @classmethod
    def get_tzinfo_instance(cls, tzinfo):
        '''Get timezone instance from tzinfo string or instance'''
        try:
            return timezone(tzinfo)  # AttributeError if tzinfo instance
        except (AttributeError, TypeError, ValueError):
            if tzinfo is None:
                return timezone(cls.DEFAULTS.tzinfo)
            return tzinfo

    @classmethod
    def get_tzinfo_name(cls, tzinfo):
        '''Get timezone name from tzinfo string or instance'''
        try:
            return tzinfo.name  # pendulum
        except AttributeError:
            if tzinfo is None:
                return cls.DEFAULTS.tzinfo
            return str(tzinfo)  # pytz or tzinfo string

    def deflex(self, truncate=False):
        '''Deflex instance by creating copy with parent DatetimeClass'''
        try:
            return DatetimeClass.instance(self)  # raise if no instance method
        except AttributeError:
            dt_info = self.form_info(self, truncate=truncate, tz_instance=True)
            return DatetimeClass(**dt_info._asdict())

    def astimezone(self, tz):
        '''Astimezone converts flextime instance to the given time zone'''
        super_astimezone = super(FlexTime, self).astimezone
        try:
            # raise TypeError if DatetimeClass requires tzinfo (e.g. datetime)
            dt = super_astimezone(self.get_tzinfo_name(tz))
        except TypeError:  # ...argument 1 must be datetime.tzinfo, not unicode
            dt = super_astimezone(self.get_tzinfo_instance(tz))

        dt.granularity = self.granularity
        dt.info = self.form_info(dt, granularity=self.granularity,
                                 truncate=False, default=False)
        return dt

    def copy(self):
        '''Copy flextime instance'''
        try:
            dt = super(FlexTime, self).copy()  # raise if no DatetimeClass.copy
            dt.granularity = self.granularity
            dt.info = self.info
        except AttributeError:
            dt = self.instance(self, self.granularity, truncate=False)
        return dt

    @classmethod
    def cast(cls, dt, granularity=None):
        '''Cast datetime or dtinfo to flextime at given granularity'''
        if (isinstance(dt, FlexTime) and (
                not granularity or
                dt.granularity == cls.Granularity(granularity))):
            return dt
        return cls.instance(dt, granularity, truncate=True)

    @classmethod
    def instance(cls, dt, granularity=None, truncate=False):
        '''
        Instance

        I/O:
        dt: a flextime, datetime, dtinfo namedtuple or plain tuple
        granularity=None: a granularity or the integer value
        truncate=False: if True, values past granularity are removed
        return: new datetime instance with granularity and datetime info
        '''
        granularity = cls.determine_granularity(dt, granularity)
        dt_info = cls.form_info(dt, granularity, truncate=truncate,
                                default=True)
        inst = cls(**dt_info._asdict())

        if granularity != inst.granularity:
            inst.granularity = granularity
            inst.info = cls.form_info(
                inst, granularity, truncate=truncate, default=False)
        return inst

    def __new__(cls, year=None, month=None, day=None,
                hour=None, minute=None, second=None, microsecond=None,
                tzinfo=None, **kwds):
        tzinfo = cls.get_tzinfo_name(tzinfo)
        dt_info = DatetimeInfo(
            year, month, day, hour, minute, second, microsecond, tzinfo)
        granularity = cls.determine_granularity(dt_info)
        super_kwds = cls.form_info(
            dt_info, granularity, default=True)._asdict()
        super_kwds.update(kwds)
        inst = super(FlexTime, cls).__new__(cls, **super_kwds)
        inst.granularity = granularity
        inst.info = dt_info
        return inst

    def __init__(self, year=None, month=None, day=None,
                 hour=None, minute=None, second=None, microsecond=None,
                 tzinfo=None, **kwds):
        super_kwds = self.form_info(
            self.info, self.granularity, default=True)._asdict()
        super_kwds.update(kwds)
        super(FlexTime, self).__init__(**super_kwds)

    def __repr__(self):
        return ('{cls}.instance({info}, granularity={granularity})'
                .format(cls=self.__class__.__name__, info=self.info,
                        granularity=self.granularity.value))

    # Comparison Operators

    def __eq__(self, other):
        try:
            return (self.granularity == other.granularity and
                    self.info == other.info and
                    super(FlexTime, self).__eq__(other))
        except AttributeError:
            return super(FlexTime, self).__eq__(other)

    def __ne__(self, other):
        return not (self == other)

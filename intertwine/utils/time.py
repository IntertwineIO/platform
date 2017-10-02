#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from collections import namedtuple
from enum import Enum
from itertools import chain
from types import MethodType

from pendulum import Pendulum as DatetimeClass
from pendulum import timezone


UTC = 'UTC'

DatetimeInfo = namedtuple(
    'DatetimeInfo',
    'year, month, day, hour, minute, second, microsecond, tzinfo')


# TODO: obtain timezone based on geo


def astimezone(self, tz):
    '''Astimezone converts FlexTime datetime to the given time zone'''
    deflexed = self.deflex()
    try:
        localized = deflexed.astimezone(FlexTime.get_timezone_name(tz))
    except:
        localized = deflexed.astimezone(FlexTime.get_timezone(tz))

    granularity = self.granularity
    dt_info = FlexTime.create_datetime_info(localized)
    FlexTime.add_flex_members(localized, granularity, dt_info)
    return localized


def deflex(self):
    '''Deflex instance by creating copy without FlexTime features'''
    try:
        return DatetimeClass.instance(self)  # Pendulum
    except AttributeError:
        dt_info = FlexTime.create_datetime_info(
            self, default=True, tz_instance=True)
        return DatetimeClass(**dt_info._asdict())


class FlexTime(DatetimeClass):
    '''
    FlexTime

    A datetime constructor to enable varying degrees of granularity
    based on the time unit components, ranging from year to microsecond.
    Each instance is a datetime that has been truncated to the specified
    granularity by substituting default values. Each instance keeps
    track of its granularity and datetime info tuple.
    '''
    Granularity = Enum('Granularity', DatetimeInfo._fields[:-1])
    MAX_GRANULARITY = tuple(Granularity)[-1]
    DEFAULTS = DatetimeInfo(None, 1, 1, 0, 0, 0, 0, UTC)
    NULLS = DatetimeInfo(*(None for _ in range(len(DatetimeInfo._fields))))

    @classmethod
    def determine_granularity(cls, dt, granularity=None):
        '''
        Determine granularity

        If granularity provided, return corresponding enum instance.
        If dt has a valid granularity member variable, return it.
        If dt is a datetime instance, return MAX GRANULARITY.
        If dt is a DatetimeInfo namedtuple, derive granularity,
            validate there are no gaps, and return it.

        I/O:
        dt: either a datetime instance or a DatetimeInfo namedtuple
        granularity=None: either a granularity or the integer value
        return: granularity enum instance per above
        '''
        if granularity is not None:
            return cls.Granularity(granularity)

        try:
            return cls.Granularity(dt.granularity)  # ValueError if None
        except (AttributeError, ValueError):
            pass

        try:
            # Create dt tuple without tzinfo
            dt_tuple = dt[:cls.MAX_GRANULARITY.value]  # TypeError if dt inst
        except TypeError:
            return cls.MAX_GRANULARITY
        else:
            has_value_tuple = tuple(t is not None for t in dt_tuple)
            gval = sum(has_value_tuple)
            check_sum = sum(has_value_tuple[:gval])
            if check_sum < gval:
                raise ValueError(
                    'One or more gaps in datetime info tuple: {}'.format(dt))
            return cls.Granularity(gval)

    @classmethod
    def get_timezone(cls, tzinfo):
        '''Get timezone instance from tzinfo string or instance'''
        try:
            return timezone(tzinfo)  # AttributeError if tzinfo instance
        except (AttributeError, TypeError, ValueError):
            if tzinfo is None:
                return timezone(cls.DEFAULTS.tzinfo)
            return tzinfo

    @classmethod
    def get_timezone_name(cls, tzinfo):
        '''Get timezone name from tzinfo string or instance'''
        try:
            return tzinfo.name  # pendulum
        except AttributeError:
            if tzinfo is None:
                return cls.DEFAULTS.tzinfo
            return str(tzinfo)  # pytz or DatetimeInfo

    @classmethod
    def create_datetime_info(cls, dt, granularity=None, default=False,
                             tz_instance=False):
        '''
        Create datetime info

        I/O:
        dt: either a datetime instance or a DatetimeInfo namedtuple
        granularity=None: either a granularity or the integer value
        default=False: when True, defaults units beyond granularity;
            when False, nullify units beyond granularity
        return: datetime info namedtuple
        '''
        granularity = cls.determine_granularity(dt, granularity)
        gval = cls.Granularity(granularity).value
        maxval = cls.MAX_GRANULARITY.value
        fields = DatetimeInfo._fields
        source = cls.DEFAULTS if default else cls.NULLS
        filled = (getattr(dt, field) for field in fields[:gval])
        unfilled = (source[i] for i in range(gval, maxval))
        tzinfo = ((cls.get_timezone(dt.tzinfo),) if tz_instance
                  else (cls.get_timezone_name(dt.tzinfo),))
        return DatetimeInfo(*chain(filled, unfilled, tzinfo))

    @classmethod
    def cast(cls, dt, granularity=None):
        '''Cast datetime to FlexTime datetime, given an optional granularity'''
        try:
            dt.granularity, dt.datetime_info
        except AttributeError:
            dt = cls.instance(dt, granularity)
        return dt

    @classmethod
    def instance(cls, dt, granularity=None, *args, **kwds):
        '''
        Instance

        I/O:
        dt: either a datetime instance or a DatetimeInfo namedtuple
        granularity=None: either a granularity or the integer value
        return: new datetime instance with granularity and datetime info
        '''
        # Short-circuit if dt is a DatetimeInfo namedtuple
        if granularity is None:
            try:
                return cls(**dt._asdict())
            except AttributeError:
                pass

        params = cls.create_datetime_info(dt, granularity)
        return cls(**params._asdict())

    @classmethod
    def add_flex_members(cls, inst, granularity, dt_info):
        '''Add flex members to instance given granularity and dt_info'''
        inst.granularity = granularity
        inst.datetime_info = dt_info
        inst.astimezone = MethodType(astimezone, inst)
        inst.deflex = MethodType(deflex, inst)

    def __new__(cls, year=None, month=None, day=None,
                hour=None, minute=None, second=None, microsecond=None,
                tzinfo=None, *args, **kwds):
        tzinfo = cls.get_timezone_name(tzinfo)
        dt_info = DatetimeInfo(
            year, month, day, hour, minute, second, microsecond, tzinfo)
        granularity = cls.determine_granularity(dt_info)
        params = cls.create_datetime_info(
            dt_info, granularity, default=True)._asdict()
        params.update(kwds)
        inst = DatetimeClass(*args, **params)
        cls.add_flex_members(inst, granularity, dt_info)
        return inst

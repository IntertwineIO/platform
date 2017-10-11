#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from collections import namedtuple

import pendulum
from sqlalchemy import (Column,
                        # ForeignKey,
                        Index, orm, types)
# from titlecase import titlecase

from intertwine import IntertwineModel
# from intertwine.third_party import urlnorm
from intertwine.utils.mixins import AutoTimestampMixin
from intertwine.utils.time import FlexTime, UTC

BaseContentModel = IntertwineModel


class Content(AutoTimestampMixin, BaseContentModel):
    '''
    Content
    '''
    _title = Column(types.String(512))
    _author_names = Column(types.String(128))

    # TODO: split out ContentPublication as 1:1?
    _publication = Column(types.String(64))  # e.g. Nature
    _published_timestamp = Column(types.DateTime(), index=True)  # UTC
    _granularity_published = Column(types.SmallInteger())
    _tzinfo_published = Column(types.String(64))
    publisher = Column(types.String(64))  # e.g. Macmillan Science & Education
    summary = Column(types.Text())
    full_text = Column(types.Text())
    # problems
    # orgs
    # geos
    # communities
    # ratings
    # comments

    __table_args__ = (Index('ux_content',
                            # ux for unique index
                            '_title',
                            '_author_names',
                            '_publication',
                            '_published_timestamp',
                            unique=True),)

    Key = namedtuple('ContentKey',  # add publisher?
                     'title, author_names, publication, published_timestamp')

    @classmethod
    def create_key(cls, title, author_names, publication, published_timestamp,
                   **kwds):
        '''Create Content key'''
        lowered_title = title.lower()
        normalized_authors = cls.normalize_author_names(author_names)
        dt_utc = published_timestamp.astimezone(UTC)
        return cls.Key(lowered_title, normalized_authors, publication, dt_utc)

    def derive_key(self):
        '''Derive Content key from instance'''
        return self.__class__.Key(
            self.title.lower(), self.author_names, self.publication,
            self.published_timestamp.astimezone(UTC))

    @property
    def title(self):
        return self._title.capitalize() if self._title else self._title

    @title.setter
    def title(self, val):
        if val is None:
            raise ValueError('Cannot be set to None')
        # During __init__()
        if self._title is None:
            self._title = val.lower()
            return
        # Not during __init__()
        key = self.__class__.create_key(
            val, self.author_names, self.publication,
            self.published_timestamp.astimezone(UTC))
        self.register_update(key)

    title = orm.synonym('_title', descriptor=title)

    @property
    def author_names(self):
        return self._author_names

    @author_names.setter
    def author_names(self, val):
        if val is None:
            raise ValueError('Cannot be set to None')
        normalized_val = self.normalize_author_names(val)
        # During __init__()
        if self._author_names is None:
            self._author_names = normalized_val
            return
        # Not during __init__()
        key = self.__class__.create_key(
            self.title, normalized_val, self.publication,
            self.published_timestamp.astimezone(UTC))
        self.register_update(key)

    author_names = orm.synonym('_author_names', descriptor=author_names)

    @classmethod
    def normalize_author_names(cls, author_names):
        author_name_list = [an.strip()
                            for an in author_names.title().split(',')]
        sorted_author_names = sorted(
            author_name_list, key=lambda x: (x.split()[-1], x.split()[:-1]))
        return ', '.join(sorted_author_names)

    @property
    def publication(self):
        return self._publication

    @publication.setter
    def publication(self, val):
        if val is None:
            val = ''
        # During __init__()
        if self._publication is None:
            self._publication = val
            return
        # Not during __init__()
        key = self.__class__.create_key(
            self.title, self.author_names, val,
            self.published_timestamp.astimezone(UTC))
        self.register_update(key)

    publication = orm.synonym('_publication', descriptor=publication)

    @property
    def published_timestamp(self):
        flex_dt = FlexTime.instance(self._published_timestamp)
        localized = flex_dt.astimezone(self.tzinfo_published)
        return FlexTime.instance(localized, self.granularity_published)

    @published_timestamp.setter
    def published_timestamp(self, val):
        '''Set published timestamp given FlexTime datetime or TimestampInfo'''
        self.set_published_timestamp_info(val)

    published_timestamp = orm.synonym('_published_timestamp',
                                      descriptor=published_timestamp)

    @property
    def granularity_published(self):
        return FlexTime.Granularity(self._granularity_published)

    granularity_published = orm.synonym('_granularity_published',
                                        descriptor=granularity_published)

    @property
    def tzinfo_published(self):
        return self._tzinfo_published

    tzinfo_published = orm.synonym('_tzinfo_published',
                                   descriptor=tzinfo_published)

    @property
    def published_timestamp_info(self):
        '''Get publication datetime info namedtuple'''
        return self.published_timestamp.info

    def set_published_timestamp_info(self, dt, granularity=None, geo=None):
        '''
        Set publication timestamp info

        Set all fields related to published timestamp. This is the only
        method that actually sets the private member variables.

        Content may be published with varying levels of granularity,
        ranging from year to microseconds. This is supported by the
        FlexTime factory class which endows datetime instances with
        granularity and info members.

        I/O:
        dt: FlexTime or regular datetime instance or DatetimeInfo tuple
        granularity=None: FlexTime granularity or associated int value
        geo=None: geo where the content was originally published
        '''

        # TODO: if geo and dt is naive, set timezone based on geo

        flex_dt = FlexTime.cast(dt, granularity)
        granularity, info = flex_dt.granularity, flex_dt.info

        now = pendulum.utcnow()
        if flex_dt > now:
            raise ValueError('Publication date may not be in the future')

        # During __init__()
        if self._published_timestamp is None:
            self._published_timestamp = flex_dt.astimezone(UTC)
        else:  # Not during __init__()
            key = self.__class__.create_key(
                self.title, self.author_names, self.publication, flex_dt)
            self.register_update(key)

        self._granularity_published = granularity.value
        self._tzinfo_published = info.tzinfo

    def __init__(self, title, author_names, publication, published_timestamp,
                 granularity_published=None, geo=None, publisher=None,
                 summary=None, full_text=None):
        self.set_published_timestamp_info(
            published_timestamp, granularity_published, geo)
        self.title = title
        self.author_names = author_names
        self.publication = publication
        self.publisher = publisher
        self.summary = summary
        self.full_text = full_text

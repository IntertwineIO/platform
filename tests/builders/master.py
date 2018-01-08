#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Master builder for instantiating test data
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import datetime
import string
import sys
from functools import partial

import pendulum
from faker import Faker

from intertwine import IntertwineModel
from intertwine.utils.tools import derive_args

LETTERS = string.letters if sys.version_info < (3,) else string.ascii_letters

SQLALCHEMY_MODEL_BASE = IntertwineModel


class Builder(object):

    MODEL_BUILDER_TAG = 'Builder'
    BUILDER_FIELD_TAG = 'builder'
    BUILD_FIELD_TAG = 'build'
    DEFAULT_FIELD_TAG = 'default'

    DEFAULT_MAX_STRING_LENGTH = 255
    DEFAULT_ALPHABET = LETTERS + string.digits + string.punctuation
    DEFAULT_TEXT = '''
    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do
    eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim
    ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut
    aliquip ex ea commodo consequat. Duis aute irure dolor in
    reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla
    pariatur. Excepteur sint occaecat cupidatat non proident, sunt in
    culpa qui officia deserunt mollit anim id est laborum.
    '''
    DEFAULT_WORDS = DEFAULT_TEXT.split()
    NOW = pendulum.now()
    SEED = int(NOW.strftime('%Y%m%d'))  # Daily seed: YYYYMMDD

    fake = Faker()
    fake.seed(SEED)
    random = fake.random  # All random usages should use this

    _builder_count = 0

    def build(self, _query_on_miss=False, _stack=None, **kwds):

        self.instance_id = self._instance_count
        self._instance_count += 1

        unique_id = self.unique_id
        stack = _stack if _stack else []
        stack.append(unique_id)

        self.model_init_kwds = kwds.copy()
        arg_names = derive_args(self.model.__init__, include_self=False,
                                include_private=False,
                                include_optional=self.optional)

        for arg in arg_names:
            if arg in kwds:
                continue
            try:
                field_builder = self.get_field_builder(field_name=arg, **kwds)
            except AttributeError:
                # Skip any argument without an instrumented attribute
                continue
            else:
                self.model_init_kwds[arg] = field_builder(_stack=stack)

        stack.pop()
        inst, created = self.model.get_or_create(
            _query_on_miss=_query_on_miss, _save=False, **self.model_init_kwds)
        return inst

    @classmethod
    def get_model_map(cls):
        '''Build model map from configured SQLAlchemy declarative base'''
        try:
            return cls._model_map
        except AttributeError:
            base = SQLALCHEMY_MODEL_BASE
            cls._model_map = {model.__name__: model
                              for model in base._decl_class_registry.values()
                              if hasattr(model, '__table__')}
            return cls._model_map

    @classmethod
    def get_model(cls, name=None):
        '''Get specified model or builder-implied model from model map'''
        if not name:
            name = cls.__name__.split(cls.MODEL_BUILDER_TAG)[0]
        try:
            return cls.get_model_map()[name]
        except KeyError:
            if not name and cls is Builder:
                raise TypeError('Base {cls} has no model'.format(cls=cls))
            raise TypeError('No model found for {name}'.format(name=name))

    @classmethod
    def get_builder(cls, name):
        '''Get specified builder by name from subclasses'''
        try:
            builder_map = Builder._builder_map
        except AttributeError:
            # import required to populate subclasses
            from tests.builders import builders  # noqa: ignore=F401

            builder_map = Builder._builder_map = {
                b.__name__: b for b in Builder.__subclasses__()}
        return builder_map[name]

    @classmethod
    def get_model_builder(cls, model):
        '''Get builder class for given model'''
        model_name = model.__name__
        model_builder_name = ''.join((model_name, cls.MODEL_BUILDER_TAG))
        try:
            return cls.get_builder(model_builder_name)
        except KeyError:
            return cls

    def get_field_builder(self, field_name, **kwds):
        '''Get specified field builder by field name or default'''
        build_field_name = '_'.join((self.BUILD_FIELD_TAG, field_name))
        field_builder = getattr(self, build_field_name, None)
        if not field_builder:
            field_builder = self.get_default_field_builder(field_name, **kwds)
        return field_builder

    def get_default_field_builder(self, field_name, **kwds):
        '''Get default field/model builder from specified field type'''
        model = self.model
        try:
            related_model = model.related_model(field_name)
            related_builder = self.__class__(model=related_model, derive=True)
            related_builder_field = '_'.join((field_name,
                                              self.BUILDER_FIELD_TAG))
            setattr(self, related_builder_field, related_builder)
            return related_builder.build

        except AttributeError:
            field = model.instrumented_attribute(field_name)
            field_type = field.expression.type
            field_type_name = field_type.__class__.__name__
            build_default_type_name = '_'.join((self.DEFAULT_FIELD_TAG,
                                                field_type_name.lower()))
            build_default_type = getattr(self, build_default_type_name)
            return partial(build_default_type, field_type=field_type, **kwds)

    def default_boolean(self, field_type, **kwds):
        '''Default random boolean value'''
        return bool(self.random.randint(0, 1))

    def default_datetime(self, field_type, **kwds):
        '''Default random datetime value'''
        now = datetime.datetime.utcnow()
        start = datetime.datetime(1900, 1, 1)
        naive_dt = self.fake.date_time_between_dates(datetime_start=start,
                                                     datetime_end=now)
        utc_tz = pendulum.timezone('UTC')
        utc_dt = utc_tz.convert(naive_dt)
        local_tz_name = self.fake.timezone()
        local_tz = pendulum.timezone(local_tz_name)
        local_dt = local_tz.convert(utc_dt)
        return local_dt

    def default_float(self, field_type, **kwds):
        '''Default random float value'''
        maxsize = sys.maxsize
        max_divisor_power = len(str(maxsize))
        divisor_power = self.random.randint(0, max_divisor_power)
        divisor = 10 ** divisor_power
        return self.random.randint(-maxsize - 1, maxsize) / divisor

    def default_integer(self, field_type, **kwds):
        '''Default random integer value'''
        return self.random.randint(-sys.maxsize - 1, sys.maxsize)

    def default_string(self, field_type, **kwds):
        '''Default random string value'''
        field_length = field_type.length
        num_chars = (self.random.randint(1, field_length) if field_length
                     else self.DEFAULT_MAX_STRING_LENGTH)
        if num_chars < 5:
            characters = []
            for i in range(num_chars):
                characters.append(self.random.choice(string.lowercase))
            return ''.join(characters)

        default_text = self.default_text(field_type, max_length=num_chars)
        return default_text[:field_length]

    def default_text(self, field_type, max_length=None, **kwds):
        '''Default random text value'''
        num_words = self.random.randint(1, len(self.DEFAULT_WORDS))
        words = []
        length = -1  # First word has no space
        for i in range(num_words):
            random_word = self.random.choice(self.DEFAULT_WORDS)
            length += len(random_word) + 1
            words.append(random_word)
            if max_length and length >= max_length - 1:
                break
        rejoined = ' '.join(words)
        capitalized = '. '.join(s.capitalize() for s in rejoined.split('. '))
        return capitalized

    @property
    def unique_id(self):
        return '.'.join((self.__class__.__name__,
                         str(self.builder_id), str(self.instance_id)))

    def __new__(cls, model=None, derive=True, **kwds):

        if derive and model:
            model_builder_class = cls.get_model_builder(model)
            if model_builder_class is not cls:
                inst = model_builder_class.__new__(
                    model_builder_class, model=model, derive=False, **kwds)
                inst.__init__(model=model, derive=False, **kwds)
                return inst

        return super(Builder, cls).__new__(cls)

    def __init__(self, model=None, derive=True, optional=False, **kwds):

        super(Builder, self).__init__()
        cls = self.__class__
        if not model:
            model = self.get_model()
        self.model = model
        self.optional = optional
        self.builder_id = cls._builder_count
        cls._builder_count += 1
        self._instance_count = 0

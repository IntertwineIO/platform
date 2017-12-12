#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Builders for instantiating test data
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import random
import string
import sys
from functools import partial

from sqlalchemy.orm.attributes import InstrumentedAttribute

from intertwine.trackable import Trackable
from intertwine.utils.tools import derive_required_args


class Builder(object):

    MODEL_BUILDER_TAG = 'Builder'
    BUILD_FIELD_TAG = 'build'
    DEFAULT_FIELD_TAG = 'default'

    DEFAULT_ALPHABET = string.digits + string.letters + string.punctuation
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

    _builder_count = 0

    def build(self, **kwds):

        self.instance_id = self._instance_count
        self._instance_count += 1

        model_init_kwds = kwds.copy()
        required_args = derive_required_args(self.model.__init__)

        for arg in required_args:
            if arg in kwds:
                continue

            field_builder = self.get_field_builder(arg)
            if field_builder:
                model_init_kwds[arg] = field_builder(**kwds)

        return self.model(**model_init_kwds)

    @classmethod
    def get_builder(cls, name):

        try:
            builder_map = Builder._builder_map
        except AttributeError:
            builder_map = Builder._builder_map = {
                b.__name__: b for b in Builder.__subclasses__()}
        return builder_map[name]

    @classmethod
    def get_model_builder(cls, model):

        model_name = model.__name__
        model_builder_name = ''.join((model_name, cls.MODEL_BUILDER_TAG))
        model_builder_class = cls.get_builder(model_builder_name)
        return model_builder_class(model)

    def get_field_builder(self, field_name):

        build_field_name = '_'.join((self.BUILD_FIELD_TAG, field_name))
        return getattr(self, build_field_name,
                       self.get_default_field_builder(field_name))

    def get_default_field_builder(self, field_name):

        model = self.model
        try:
            related_model = model.related_model(field_name)
            related_builder = self.get_model_builder(related_model)
            return related_builder.build

        except AttributeError:
            field = getattr(model, field_name)

            # Find underlying field if field is a synonym
            if not isinstance(field, InstrumentedAttribute):
                underlying_field_name = field.property.key
                field = getattr(model, underlying_field_name)

            field_type = field.expression.type
            field_type_name = field_type.__class__.__name__
            build_default_type_name = '_'.join((self.DEFAULT_FIELD_TAG,
                                                field_type_name.lower()))
            build_default_type = getattr(self, build_default_type_name)
            return partial(build_default_type, field_type=field_type)

    def default_boolean(self, field_type, **kwds):
        return bool(random.randint(0, 1))

    def default_integer(self, field_type, **kwds):
        return random.randint(-sys.maxsize - 1, sys.maxsize)

    def default_string(self, field_type, **kwds):
        field_length = field_type.length
        num_chars = random.randint(1, field_length)
        if num_chars < 5:
            characters = []
            for i in range(num_chars):
                characters.append(random.choice(string.lowercase))
            return ''.join(characters)

        default_text = self.default_text(field_type, max_length=field_length)
        return default_text[:field_length]

    def default_text(self, field_type, max_length=None, **kwds):
        num_words = random.randint(1, len(self.DEFAULT_WORDS))
        words = []
        length = -1  # First word has no space
        for i in range(num_words):
            random_word = random.choice(self.DEFAULT_WORDS)
            length += len(random_word) + 1
            words.append(random_word)
            if max_length and length >= max_length - 1:
                break
        return ' '.join(words).capitalize()

    def __init__(self, model=None):
        cls = self.__class__
        if not model:
            model_name = cls.__name__.split(
                self.MODEL_BUILDER_TAG)[0]
            model = Trackable._classes[model_name]
        self.model = model
        self.builder_id = cls._builder_count
        cls._builder_count += 1
        self._instance_count = 0


class ProblemBuilder(Builder):

    NAMES = {
        'Poverty',
        'Homelessness',
        'Domestic Violence',
        'Substance Abuse'
    }

    def build_name(self):
        return random.choice(tuple(self.NAMES))


class ProblemConnectionBuilder(Builder):

    def build_axis(self):
        return random.choice(tuple(self.model.AXES))

    def build_problem_a(self):
        return
        return random.choice(tuple(self.model.AXES))

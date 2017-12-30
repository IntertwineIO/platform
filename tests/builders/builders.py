#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Builders for instantiating test data
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
from intertwine.utils.space import Area, Coordinate, GeoLocation
from intertwine.utils.tools import derive_args

SQLALCHEMY_MODEL_BASE = IntertwineModel


class Builder(object):

    MODEL_BUILDER_TAG = 'Builder'
    BUILDER_FIELD_TAG = 'builder'
    BUILD_FIELD_TAG = 'build'
    DEFAULT_FIELD_TAG = 'default'

    DEFAULT_MAX_STRING_LENGTH = 255
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
    def get_builder(cls, name):

        try:
            builder_map = Builder._builder_map
        except AttributeError:
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

    @classmethod
    def get_model_map(cls, base):
        '''Build model map given SQLAlchemy declarative base'''
        try:
            return cls._model_map
        except AttributeError:
            cls._model_map = {model.__name__: model
                              for model in base._decl_class_registry.values()
                              if hasattr(model, '__table__')}
            return cls._model_map

    def get_field_builder(self, field_name, **kwds):

        build_field_name = '_'.join((self.BUILD_FIELD_TAG, field_name))
        return getattr(self, build_field_name,
                       self.get_default_field_builder(field_name, **kwds))

    def get_default_field_builder(self, field_name, **kwds):

        model = self.model
        try:
            related_model = model.related_model(field_name)
            # related_builder_class = self.get_model_builder(related_model)
            related_builder = self.__class__(model=related_model, derive=True)
            related_builder_field = '_'.join((field_name,
                                              self.BUILDER_FIELD_TAG))
            setattr(self, related_builder_field, related_builder)
            return related_builder.build

        except AttributeError:
            # field = getattr(model, field_name)
            field = model.instrumented_attribute(field_name)
            field_type = field.expression.type
            field_type_name = field_type.__class__.__name__
            build_default_type_name = '_'.join((self.DEFAULT_FIELD_TAG,
                                                field_type_name.lower()))
            build_default_type = getattr(self, build_default_type_name)
            return partial(build_default_type, field_type=field_type, **kwds)

    def default_boolean(self, field_type, **kwds):
        return bool(self.random.randint(0, 1))

    def default_datetime(self, field_type, **kwds):
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
        maxsize = sys.maxsize
        max_divisor_power = len(str(maxsize))
        divisor_power = self.random.randint(0, max_divisor_power)
        divisor = 10 ** divisor_power
        return self.random.randint(-maxsize - 1, maxsize) / divisor

    def default_integer(self, field_type, **kwds):
        return self.random.randint(-sys.maxsize - 1, sys.maxsize)

    def default_string(self, field_type, **kwds):
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
        num_words = self.random.randint(1, len(self.DEFAULT_WORDS))
        words = []
        length = -1  # First word has no space
        for i in range(num_words):
            random_word = self.random.choice(self.DEFAULT_WORDS)
            length += len(random_word) + 1
            words.append(random_word)
            if max_length and length >= max_length - 1:
                break
        return ' '.join(words).capitalize()

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
            model_name = cls.__name__.split(self.MODEL_BUILDER_TAG)[0]
            model = self.get_model_map(SQLALCHEMY_MODEL_BASE)[model_name]
        self.model = model
        self.optional = optional
        self.builder_id = cls._builder_count
        cls._builder_count += 1
        self._instance_count = 0


class ProblemBuilder(Builder):

    NAMES = {
        'You Know Who',
        'The Dark Arts',
        'Orphaned',
        'Identity Crisis',
        'Daddy Issues',
        'Mommy Issues',
        'A Cursed Broomstick',
        'Bludgeoned by Bludgers',
        'Pummeled by Whomping Willow',
        'Trolls in the Bathroom',
        'Paralyzed by a Basilisk',
        'Contaminated Polyjuice Potion',
        'Singed by Dragonfire',
        'A Broken Wand',
        'A Lost Pet',
        'Flying Car Taken for Joy Ride',
        'Afflicted by Full Body-Bind Curse',
        'Vomiting Slugs',
        'Memory Loss',
    }

    def build_name(self, **kwds):
        included_names = self.include or self.NAMES
        excluded_names = self.exclude
        names = included_names - excluded_names
        return self.random.choice(tuple(names))

    def __init__(self, model=None, include=None, exclude=None, **kwds):
        self.include = include or set()
        self.exclude = exclude or set()
        super(ProblemBuilder, self).__init__(**kwds)


class ProblemConnectionBuilder(Builder):
    '''
    ProblemConnectionBuilder

    If the net includes contains 2 or more names, both problem names are
    selected from these names. If the net includes contains 1 name, the
    name is randomly assigned to problem A or problem B, with the other
    name selected randomly from the default list of problem names.
    for
    I/O:
    include=None: set of problem names to include
    exclude=None: set of problem names to exclude
    '''

    def build(self, **kwds):
        net_include = self.include - self.exclude
        self.problem_position = (
            self.random.choice((self.model.PROBLEM_A, self.model.PROBLEM_B))
            if len(net_include) == 1 else None)

        return super(ProblemConnectionBuilder, self).build(**kwds)

    def build_axis(self, **kwds):
        return self.random.choice(tuple(self.model.AXES))

    def build_problem_a(self, _stack=None, **kwds):
        PROBLEM_A, PROBLEM_B = self.model.PROBLEM_A, self.model.PROBLEM_B
        additional_exclude = (
            {self.model_init_kwds[PROBLEM_B].name}
            if PROBLEM_B in self.model_init_kwds else set())

        exclude = self.exclude | additional_exclude
        original_net_include = self.include - self.exclude
        net_include = original_net_include - additional_exclude
        include = (net_include
                   if ((net_include and self.problem_position == PROBLEM_A) or
                       len(original_net_include) > 1)
                   else None)

        self.problem_a_builder = ProblemBuilder(include=include,
                                                exclude=exclude)
        return self.problem_a_builder.build(_stack=_stack)

    def build_problem_b(self, _stack=None, **kwds):
        PROBLEM_A, PROBLEM_B = self.model.PROBLEM_A, self.model.PROBLEM_B
        additional_exclude = (
            {self.model_init_kwds[PROBLEM_A].name}
            if PROBLEM_A in self.model_init_kwds else set())

        exclude = self.exclude | additional_exclude
        original_net_include = self.include - self.exclude
        net_include = original_net_include - additional_exclude
        include = (net_include
                   if ((net_include and self.problem_position == PROBLEM_B) or
                       len(original_net_include) > 1)
                   else None)

        self.problem_b_builder = ProblemBuilder(include=include,
                                                exclude=exclude)
        return self.problem_b_builder.build(_stack=_stack)

    def __init__(self, model=None, include=None, exclude=None, **kwds):
        self.include = include or set()
        self.exclude = exclude or set()
        super(ProblemConnectionBuilder, self).__init__(**kwds)


class ProblemConnectionRatingBuilder(Builder):

    def build_rating(self, **kwds):
        model = self.model
        return self.random.randint(model.MIN_RATING, model.MAX_RATING)

    def build_weight(self, **kwds):
        model = self.model
        return self.random.randint(model.MIN_WEIGHT, model.MAX_WEIGHT)

    def build_connection(self, _stack=None, **kwds):
        if 'problem' in self.model_init_kwds:
            problem = self.model_init_kwds['problem']
            include = {problem.name}
        else:
            include = None

        self.connection_builder = ProblemConnectionBuilder(include=include)
        return self.connection_builder.build(_stack=_stack)

    def build_problem(self, _stack=None, **kwds):
        if 'connection' in self.model_init_kwds:
            connection = self.model_init_kwds['connection']
            include = {connection.problem_a.name, connection.problem_b.name}
        else:
            include = None

        self.problem_builder = ProblemBuilder(include=include)
        return self.problem_builder.build(_stack=_stack)

    def build_org(self, **kwds):
        self.org_builder = OrgBuilder()
        return self.org_builder.build()


class AggregateProblemConnectionRatingBuilder(Builder):

    MIN_RATING = -1
    MAX_RATING = 4
    MIN_WEIGHT = 0
    MAX_WEIGHT = 10 ** 10

    def build_rating(self, **kwds):
        model = self.model
        return self.random.randint(
            model.MIN_RATING * 100, model.MAX_RATING * 100) / 100

    def build_weight(self, **kwds):
        model = self.model
        return self.random.randint(model.MIN_WEIGHT, sys.maxsize)

    def build_aggregation(self, **kwds):
        model = self.model
        return self.random.choice(tuple(model.AGGREGATIONS))

    def build_connection(self, _stack=None, **kwds):
        if 'community' in self.model_init_kwds:
            community = self.model_init_kwds['community']
            problem = community.problem
            include = {problem.name}
        else:
            include = None

        self.connection_builder = ProblemConnectionBuilder(include=include)
        return self.connection_builder.build(_stack=_stack)

    def build_community(self, _stack=None, **kwds):
        if 'connection' in self.model_init_kwds:
            connection = self.model_init_kwds['connection']
            problem_include = {connection.problem_a.name,
                               connection.problem_b.name}
        else:
            problem_include = None

        self.community_builder = CommunityBuilder(
            problem_include=problem_include)
        return self.community_builder.build(_stack=_stack)

    def build_org(self, **kwds):
        self.org_builder = OrgBuilder()
        return self.org_builder.build()


class ImageBuilder(Builder):

    URLS = {
        'https://static0.srcdn.com/wp-content/uploads/2017/05/Voldemort.jpg',
        'https://qph.ec.quoracdn.net/main-qimg-'
        '266d3136d495cda1cf3946529738e901-c',
        'https://www.polyvore.com/cgi/img-thing?.out=jpg&size=l&tid=12885161'
    }

    def build_url(self, **kwds):
        return self.random.choice(tuple(self.URLS))


class OrgBuilder(Builder):

    NAMES = {
        'Hogwarts School of Witchcraft and Wizardry',
        'Durmstrang Institute',
        'Beauxbatons Academy of Magic',
        'Ministry of Magic',
        'Department of Magical Law Enforcement',
        'Department of Magical Accidents and Catastrophes',
        'Department for the Regulation and Control of Magical Creatures',
        'Department of International Magical Cooperation',
        'Department of Magical Transportation',
        'Department of Magical Games and Sports',
        'Department of Mysteries',
    }

    def build(self, **kwds):
        return self.build_name(**kwds)

    def build_name(self, **kwds):
        included_names = self.include or self.NAMES
        excluded_names = self.exclude
        names = included_names - excluded_names
        return self.random.choice(tuple(names))

    def __init__(self, model=None, include=None, exclude=None, **kwds):
        self.include = include or set()
        self.exclude = exclude or set()


class GeoBuilder(Builder):

    NAMES = {
        'Diagon Alley',
        'Forbidden Forest',
        'The Great Lake',
        'Azkaban',
        'Little Whinging',
        'Surrey',
        'London',
        'Greater London',
        'England',
        'Somewhere in the Pyrenees',
        'Andorra',
        'France',
        'The Far North of Europe',
        'Europe',
        'The Middle of the North Sea',
        'The North Sea',
    }

    def build_name(self, **kwds):
        return self.random.choice(tuple(self.NAMES))


class GeoDataBuilder(Builder):

    MIN_TOTAL_POP = 10
    MAX_TOTAL_POP = 10 ** 7
    MIN_URBAN_POP = 0
    MAX_URBAN_POP = 10 ** 7
    MIN_LATITUDE = GeoLocation.MIN_LATITUDE
    MAX_LATITUDE = GeoLocation.MAX_LATITUDE
    MIN_LONGITUDE = GeoLocation.MIN_LONGITUDE
    MAX_LONGITUDE = GeoLocation.MAX_LONGITUDE
    MIN_LAND_AREA = 10
    MAX_LAND_AREA = 10 ** 6
    MIN_WATER_AREA = 0
    MAX_WATER_AREA = 10 ** 3

    COORDINATE_PRECISION = Coordinate.DEFAULT_PRECISION
    AREA_PRECISION = Area.DEFAULT_PRECISION

    def build_total_pop(self, **kwds):
        if 'urban_pop' in self.model_init_kwds:
            urban_pop = self.model_init_kwds['urban_pop']
            minimum, maximum = urban_pop, self.MAX_TOTAL_POP
        else:
            minimum, maximum = self.MIN_TOTAL_POP, self.MAX_TOTAL_POP
        return self.random.randint(minimum, maximum)

    def build_urban_pop(self, **kwds):
        if 'total_pop' in self.model_init_kwds:
            total_pop = self.model_init_kwds['total_pop']
            minimum, maximum = self.MIN_URBAN_POP, total_pop
        else:
            minimum, maximum = self.MIN_URBAN_POP, self.MAX_URBAN_POP
        return self.random.randint(minimum, maximum)

    def build_latitude(self, **kwds):
        minimum, maximum = self.MIN_LATITUDE, self.MAX_LATITUDE
        precision = self.COORDINATE_PRECISION
        factor = 10 ** precision
        return self.random.randint(minimum * factor, maximum * factor) / factor

    def build_longitude(self, **kwds):
        minimum, maximum = self.MIN_LONGITUDE, self.MAX_LONGITUDE
        precision = self.COORDINATE_PRECISION
        factor = 10 ** precision
        return self.random.randint(minimum * factor, maximum * factor) / factor

    def build_land_area(self, **kwds):
        minimum, maximum = self.MIN_LAND_AREA, self.MAX_LAND_AREA
        precision = self.AREA_PRECISION
        factor = 10 ** precision
        return self.random.randint(minimum * factor, maximum * factor) / factor

    def build_water_area(self, **kwds):
        minimum, maximum = self.MIN_WATER_AREA, self.MAX_WATER_AREA
        precision = self.AREA_PRECISION
        factor = 10 ** precision
        return self.random.randint(minimum * factor, maximum * factor) / factor


class GeoLevelBuilder(Builder):

    def build_level(self, **kwds):
        return self.random.choice(self.model.UP.keys())


class GeoIDBuilder(Builder):

    def build_standard(self, **kwds):
        return self.random.choice(tuple(self.model.STANDARDS))


class CommunityBuilder(Builder):

    MAX_NUM_FOLLOWERS = 10 ** 9

    def build_problem(self, _stack=None, **kwds):
        self.problem_builder = ProblemBuilder(
            include=self.problem_include, exclude=self.problem_exclude)
        return self.problem_builder.build(_stack=None)

    def build_org(self, **kwds):
        self.org_builder = OrgBuilder()
        return self.org_builder.build()

    def build_num_followers(self, **kwds):
        return self.random.randint(0, self.MAX_NUM_FOLLOWERS)

    def __init__(self, model=None, problem_include=None, problem_exclude=None,
                 **kwds):
        self.problem_include = problem_include or set()
        self.problem_exclude = problem_exclude or set()
        super(CommunityBuilder, self).__init__(**kwds)


class ContentBuilder(Builder):

    MAX_AUTHORS = 5

    PUBLICATION_NAMES = {
        'The Daily Prophet',
        'The Evening Prophet',
        'The Sunday Prophet',
        'The Quibbler',
        'Wizarding Wireless Network',
        'Potterwatch',
        'Mystic, International Journal of Magic',
        'Journal of Charms & Wards',
        'Defense Against the Dark Arts',
        'Curses & Counterspells',
        'New Wizard & Witch',
        'Wizardry & Witchcraft',
        'The Magical Review',
    }

    def build_author_names(self, **kwds):
        num_authors = self.random.randint(1, self.MAX_AUTHORS)
        authors = (self.fake.name() for _ in xrange(num_authors))
        author_names = '; '.join(authors)
        return author_names

    def build_publication(self, **kwds):
        return self.random.choice(tuple(self.PUBLICATION_NAMES))
